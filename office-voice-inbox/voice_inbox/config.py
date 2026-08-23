"""Configuration: env vars > ~/.config/office-voice-inbox/.env > defaults.

The AssemblyAI key is never stored in this repo. It comes from the
environment, the .env file, or (fallback) the Obsidian APIs.md note.
Key values are never logged or printed.
"""

import os
import re
from dataclasses import dataclass, field
from pathlib import Path

CONFIG_DIR = Path("~/.config/office-voice-inbox").expanduser()
ENV_FILE = CONFIG_DIR / ".env"

_KEY_TOKEN = re.compile(r"\b([A-Za-z0-9_-]{24,})\b")


def _load_env_file(path: Path) -> dict:
    """Minimal .env parser (KEY=VALUE, # comments). No dependency needed."""
    values = {}
    if not path.is_file():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        values[key.strip()] = val.strip().strip("'\"")
    return values


def _key_from_apis_md(path: Path) -> str | None:
    """Pull the AssemblyAI key from the Obsidian APIs.md note.

    Looks for a line mentioning 'assemblyai' and takes the first long
    token on that line or the next non-empty line.
    """
    if not path.is_file():
        return None
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    for i, line in enumerate(lines):
        if "assemblyai" not in line.lower():
            continue
        for candidate in lines[i : i + 3]:
            for match in _KEY_TOKEN.finditer(candidate):
                token = match.group(1)
                if token.lower() not in ("assemblyai",) and not token.startswith("http"):
                    return token
    return None


@dataclass
class Config:
    assemblyai_api_key: str = ""
    home: Path = field(default_factory=lambda: Path("~/OfficeVoiceInbox").expanduser())
    input_device: str = ""  # name substring or index; "" = system default
    vad_aggressiveness: int = 2
    burst_end_silence_ms: int = 1500
    min_voiced_ms: int = 600
    max_burst_seconds: int = 600
    clip_retention_days: int = 3
    drive_backend: str = "docs"  # docs | rclone | off
    drive_folder_name: str = "Office Voice Inbox"
    rclone_remote: str = "gdrive"
    timezone: str = "America/Chicago"

    # Derived paths
    @property
    def clips_dir(self) -> Path:
        return self.home / "clips"

    @property
    def inbox_dir(self) -> Path:
        return self.home / "inbox"

    @property
    def state_file(self) -> Path:
        return self.home / "state.json"

    @property
    def pending_file(self) -> Path:
        return self.home / "pending-drive.jsonl"

    @property
    def drive_cache_file(self) -> Path:
        return self.home / "drive-cache.json"

    def ensure_dirs(self) -> None:
        for d in (self.home, self.clips_dir, self.inbox_dir, CONFIG_DIR):
            d.mkdir(parents=True, exist_ok=True)


def load_config() -> Config:
    env = dict(_load_env_file(ENV_FILE))
    env.update({k: v for k, v in os.environ.items() if v})

    def get(name: str, default: str) -> str:
        return env.get(name, default)

    cfg = Config(
        assemblyai_api_key=get("ASSEMBLYAI_API_KEY", ""),
        home=Path(get("VOICE_INBOX_HOME", "~/OfficeVoiceInbox")).expanduser(),
        input_device=get("INPUT_DEVICE", ""),
        vad_aggressiveness=int(get("VAD_AGGRESSIVENESS", "2")),
        burst_end_silence_ms=int(get("BURST_END_SILENCE_MS", "1500")),
        min_voiced_ms=int(get("MIN_VOICED_MS", "600")),
        max_burst_seconds=int(get("MAX_BURST_SECONDS", "600")),
        clip_retention_days=int(get("CLIP_RETENTION_DAYS", "3")),
        drive_backend=get("DRIVE_BACKEND", "docs").lower(),
        drive_folder_name=get("DRIVE_FOLDER_NAME", "Office Voice Inbox"),
        rclone_remote=get("RCLONE_REMOTE", "gdrive"),
        timezone=get("TIMEZONE", "America/Chicago"),
    )

    if not cfg.assemblyai_api_key:
        apis_md = Path(get("APIS_MD_PATH", "~/Desktop/Macbook Air/APIs.md")).expanduser()
        cfg.assemblyai_api_key = _key_from_apis_md(apis_md) or ""

    cfg.ensure_dirs()
    return cfg
