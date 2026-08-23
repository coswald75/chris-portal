"""Daily inbox entries: formatting and the local markdown source of truth.

One file per America/Chicago day, append only, one heading per burst:

    ## HH:MM CT
    [PRIORITY]            <- only when a cue fired
    transcript text
"""

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from .config import Config

DOC_TITLE_FMT = "%Y-%m-%d Office Voice Inbox"


def local_now(cfg: Config) -> datetime:
    return datetime.now(ZoneInfo(cfg.timezone))


def to_local(cfg: Config, dt: datetime) -> datetime:
    return dt.astimezone(ZoneInfo(cfg.timezone))


def day_key(cfg: Config, dt: datetime) -> str:
    return to_local(cfg, dt).strftime("%Y-%m-%d")


def doc_title(day: str) -> str:
    return f"{day} Office Voice Inbox"


def format_entry(cfg: Config, started_at: datetime, text: str, priority: bool) -> str:
    stamp = to_local(cfg, started_at).strftime("%H:%M")
    lines = [f"## {stamp} CT"]
    if priority:
        lines.append("[PRIORITY]")
    lines.append(text.strip())
    return "\n".join(lines) + "\n\n"


def local_path(cfg: Config, day: str) -> Path:
    return cfg.inbox_dir / f"{doc_title(day)}.md"


def append_local(cfg: Config, day: str, entry: str) -> Path:
    """Append to the local daily markdown. This always succeeds first;
    Drive delivery is layered on top and can retry."""
    path = local_path(cfg, day)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(entry)
    return path
