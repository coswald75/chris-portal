"""On / off / mute state shared between the daemon, CLI, and menu bar.

A tiny JSON file so any process can flip the switches. The daemon polls it.
  listening: capture session is on (menu-bar toggle / hotkey)
  muted:     mic soft-mute (hardware mute always wins, obviously)
"""

import json
import os
import tempfile
from pathlib import Path

DEFAULT_STATE = {"listening": True, "muted": False}


def read_state(path: Path) -> dict:
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
        return {**DEFAULT_STATE, **state}
    except (OSError, ValueError):
        return dict(DEFAULT_STATE)


def write_state(path: Path, **updates) -> dict:
    state = read_state(path)
    state.update(updates)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".state-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(state, fh)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    return state


def is_capturing(path: Path) -> bool:
    state = read_state(path)
    return bool(state["listening"]) and not state["muted"]
