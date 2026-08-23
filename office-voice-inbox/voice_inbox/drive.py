"""Delivery to the "Office Voice Inbox" folder in Chris's Drive.

Backends (DRIVE_BACKEND):
  docs   - Google Docs API. One Google Doc per CT day, append only.
           Needs a one-time `voice-inbox auth` with an OAuth client file.
  rclone - sync the local daily markdown into the Drive folder with rclone
           (uses whatever gdrive auth already exists on the Mac). Same shape.
  off    - local markdown only.

Entries are queued in pending-drive.jsonl and drained after every burst, so
a flaky network never loses a burst — the local markdown is always written
first regardless.
"""

import json
import logging
import subprocess
from pathlib import Path

from .config import CONFIG_DIR, Config
from .inbox import doc_title, local_path

log = logging.getLogger("voice_inbox.drive")

OAUTH_CLIENT_FILE = CONFIG_DIR / "credentials.json"
TOKEN_FILE = CONFIG_DIR / "token.json"
SCOPES = [
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/documents",
]


# ---------------------------------------------------------------- pending q

def enqueue(cfg: Config, day: str, entry: str) -> None:
    if cfg.drive_backend == "off":
        return
    with open(cfg.pending_file, "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"day": day, "entry": entry}) + "\n")


def flush(cfg: Config) -> bool:
    """Try to deliver everything pending. Returns True when the queue is empty."""
    if cfg.drive_backend == "off":
        return True
    try:
        raw = cfg.pending_file.read_text(encoding="utf-8")
    except FileNotFoundError:
        return True
    items = [json.loads(line) for line in raw.splitlines() if line.strip()]
    if not items:
        return True

    remaining = []
    if cfg.drive_backend == "rclone":
        # rclone re-copies whole daily files, so one push per distinct day.
        for day in sorted({it["day"] for it in items}):
            if not _rclone_push_day(cfg, day):
                remaining.extend(it for it in items if it["day"] == day)
    else:
        docs = None
        for i, it in enumerate(items):
            try:
                docs = docs or _DocsBackend(cfg)
                docs.append(it["day"], it["entry"])
            except Exception as exc:  # noqa: BLE001 - keep the daemon alive
                log.warning("Drive append failed (%s); will retry", exc)
                remaining.extend(items[i:])  # keep order: append-only doc
                break

    with open(cfg.pending_file, "w", encoding="utf-8") as fh:
        for it in remaining:
            fh.write(json.dumps(it) + "\n")
    return not remaining


# ---------------------------------------------------------------- rclone

def _rclone_push_day(cfg: Config, day: str) -> bool:
    src = local_path(cfg, day)
    if not src.is_file():
        return True
    dest = f"{cfg.rclone_remote}:{cfg.drive_folder_name}/{doc_title(day)}.md"
    try:
        subprocess.run(
            ["rclone", "copyto", str(src), dest],
            check=True,
            capture_output=True,
            timeout=120,
        )
        return True
    except (subprocess.SubprocessError, FileNotFoundError) as exc:
        log.warning("rclone push failed (%s); will retry", exc)
        return False


# ---------------------------------------------------------------- Docs API

class _DocsBackend:
    def __init__(self, cfg: Config):
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build

        self.cfg = cfg
        if not TOKEN_FILE.is_file():
            raise RuntimeError("not authorized — run `voice-inbox auth` once")
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
            TOKEN_FILE.chmod(0o600)
        self.drive = build("drive", "v3", credentials=creds, cache_discovery=False)
        self.docs = build("docs", "v1", credentials=creds, cache_discovery=False)
        self._cache = self._load_cache()

    def _load_cache(self) -> dict:
        try:
            return json.loads(self.cfg.drive_cache_file.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    def _save_cache(self) -> None:
        self.cfg.drive_cache_file.write_text(json.dumps(self._cache), encoding="utf-8")

    def _folder_id(self) -> str:
        if fid := self._cache.get("folder_id"):
            return fid
        name = self.cfg.drive_folder_name.replace("'", "\\'")
        res = self.drive.files().list(
            q=(
                f"name = '{name}' and "
                "mimeType = 'application/vnd.google-apps.folder' and trashed = false"
            ),
            fields="files(id)",
            pageSize=1,
        ).execute()
        if res.get("files"):
            fid = res["files"][0]["id"]
        else:
            created = self.drive.files().create(
                body={
                    "name": self.cfg.drive_folder_name,
                    "mimeType": "application/vnd.google-apps.folder",
                },
                fields="id",
            ).execute()
            fid = created["id"]
            log.info("created Drive folder %r", self.cfg.drive_folder_name)
        self._cache["folder_id"] = fid
        self._save_cache()
        return fid

    def _doc_id(self, day: str) -> str:
        key = f"doc:{day}"
        if did := self._cache.get(key):
            return did
        folder = self._folder_id()
        title = doc_title(day).replace("'", "\\'")
        res = self.drive.files().list(
            q=(
                f"name = '{title}' and '{folder}' in parents and "
                "mimeType = 'application/vnd.google-apps.document' and trashed = false"
            ),
            fields="files(id)",
            pageSize=1,
        ).execute()
        if res.get("files"):
            did = res["files"][0]["id"]
        else:
            created = self.drive.files().create(
                body={
                    "name": doc_title(day),
                    "mimeType": "application/vnd.google-apps.document",
                    "parents": [folder],
                },
                fields="id",
            ).execute()
            did = created["id"]
            log.info("created daily doc %r", doc_title(day))
        self._cache[key] = did
        self._save_cache()
        return did

    def append(self, day: str, entry: str) -> None:
        doc_id = self._doc_id(day)
        self.docs.documents().batchUpdate(
            documentId=doc_id,
            body={
                "requests": [
                    {
                        "insertText": {
                            "endOfSegmentLocation": {},
                            "text": entry,
                        }
                    }
                ]
            },
        ).execute()


def authorize() -> None:
    """One-time interactive OAuth for the docs backend. Opens a browser."""
    from google_auth_oauthlib.flow import InstalledAppFlow

    if not OAUTH_CLIENT_FILE.is_file():
        raise SystemExit(
            f"Put an OAuth client file (Desktop app) at {OAUTH_CLIENT_FILE} first.\n"
            "Google Cloud console -> APIs & Services -> Credentials -> "
            "Create OAuth client ID -> Desktop app, then download the JSON.\n"
            "Enable the Drive API and Docs API on that project. Sign in as "
            "the same account that owns the Drive (chris@sovgracekc.org)."
        )
    flow = InstalledAppFlow.from_client_secrets_file(str(OAUTH_CLIENT_FILE), SCOPES)
    creds = flow.run_local_server(port=0)
    TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
    TOKEN_FILE.chmod(0o600)
    print(f"Authorized. Token saved to {TOKEN_FILE} (never commit it).")
