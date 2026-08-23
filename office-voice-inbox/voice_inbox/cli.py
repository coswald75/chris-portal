"""voice-inbox CLI: run / on / off / mute / unmute / status / auth /
devices / stats / transcribe-one.

Usage: python -m voice_inbox.cli <command>
"""

import argparse
import sys
from pathlib import Path

from . import state as state_mod
from .config import load_config


def cmd_run(_args) -> None:
    from .daemon import run_daemon

    run_daemon()


def cmd_on(_args) -> None:
    cfg = load_config()
    state_mod.write_state(cfg.state_file, listening=True)
    print("listening: on")


def cmd_off(_args) -> None:
    cfg = load_config()
    state_mod.write_state(cfg.state_file, listening=False)
    print("listening: off")


def cmd_mute(_args) -> None:
    cfg = load_config()
    state_mod.write_state(cfg.state_file, muted=True)
    print("muted")


def cmd_unmute(_args) -> None:
    cfg = load_config()
    state_mod.write_state(cfg.state_file, muted=False)
    print("unmuted")


def cmd_status(_args) -> None:
    cfg = load_config()
    st = state_mod.read_state(cfg.state_file)
    print(f"listening: {st['listening']}  muted: {st['muted']}")
    print(f"home:      {cfg.home}")
    print(f"drive:     {cfg.drive_backend}")
    print(f"aai key:   {'found' if cfg.assemblyai_api_key else 'MISSING'}")
    pending = 0
    if cfg.pending_file.is_file():
        pending = sum(1 for line in cfg.pending_file.read_text().splitlines() if line.strip())
    print(f"pending Drive appends: {pending}")


def cmd_auth(_args) -> None:
    from . import drive

    drive.authorize()


def cmd_devices(_args) -> None:
    import sounddevice as sd

    for idx, dev in enumerate(sd.query_devices()):
        if dev["max_input_channels"] > 0:
            print(f"{idx}: {dev['name']} ({dev['max_input_channels']} ch)")


def cmd_stats(_args) -> None:
    """Prove the disk math: silence must not grow the disk (spec §4, §11)."""
    cfg = load_config()
    total = 0
    per_day: dict[str, int] = {}
    for wav in cfg.clips_dir.glob("*/*.wav"):
        size = wav.stat().st_size
        total += size
        per_day[wav.parent.name] = per_day.get(wav.parent.name, 0) + size
    for day in sorted(per_day):
        print(f"{day}: {per_day[day] / 1e6:.1f} MB")
    print(f"total gated clips: {total / 1e6:.1f} MB "
          f"(retention {cfg.clip_retention_days} days)")


def cmd_transcribe_one(args) -> None:
    """Build-order step 3: AssemblyAI transcript for one clip."""
    from .priority import is_priority
    from .transcribe import transcribe_clip

    cfg = load_config()
    text = transcribe_clip(cfg.assemblyai_api_key, Path(args.clip))
    print(text or "(no words detected)")
    if is_priority(text):
        print("[PRIORITY] cue detected")


def cmd_menubar(_args) -> None:
    from .menubar import main as menubar_main

    menubar_main()


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(prog="voice-inbox", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name, fn, help_text in [
        ("run", cmd_run, "run the capture daemon (what launchd starts)"),
        ("on", cmd_on, "turn the office session on"),
        ("off", cmd_off, "turn the office session off"),
        ("mute", cmd_mute, "soft-mute the mic"),
        ("unmute", cmd_unmute, "unmute the mic"),
        ("status", cmd_status, "show state and pending Drive appends"),
        ("auth", cmd_auth, "one-time Google authorization (docs backend)"),
        ("devices", cmd_devices, "list input devices"),
        ("stats", cmd_stats, "clip disk usage per day"),
        ("menubar", cmd_menubar, "run the menu-bar toggle app"),
    ]:
        sub.add_parser(name, help=help_text).set_defaults(fn=fn)
    p = sub.add_parser("transcribe-one", help="transcribe a single WAV clip (test)")
    p.add_argument("clip")
    p.set_defaults(fn=cmd_transcribe_one)

    args = parser.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
