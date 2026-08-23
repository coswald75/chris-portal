"""The always-running piece: capture thread + burst worker + housekeeping.

Per burst: transcribe -> priority cue check -> append to local daily
markdown -> queue + flush to Drive. Target is "nearly now": text lands in
the day's doc within a minute or two of the burst ending.
"""

import logging
import queue
import signal
import threading
import time
from datetime import datetime
from pathlib import Path

from . import drive, inbox
from .capture import CaptureThread
from .config import Config, load_config
from .priority import is_priority
from .transcribe import TranscriptionError, transcribe_clip

log = logging.getLogger("voice_inbox.daemon")

TRANSCRIBE_ATTEMPTS = 3
RETRY_BACKOFF_S = 10
CLEANUP_INTERVAL_S = 3600
DRIVE_RETRY_INTERVAL_S = 60


def process_burst(cfg: Config, clip: Path, started_at: datetime) -> None:
    text = ""
    for attempt in range(1, TRANSCRIBE_ATTEMPTS + 1):
        try:
            text = transcribe_clip(cfg.assemblyai_api_key, clip)
            break
        except Exception as exc:  # noqa: BLE001 - TranscriptionError, network, etc.
            if attempt == TRANSCRIBE_ATTEMPTS:
                log.error(
                    "giving up on %s after %d attempts (%s); clip kept %d days",
                    clip.name, attempt, exc, cfg.clip_retention_days,
                )
                return
            log.warning("transcription attempt %d failed (%s), retrying", attempt, exc)
            time.sleep(RETRY_BACKOFF_S * attempt)

    if not text:
        log.info("no words in %s; skipping", clip.name)
        return

    day = inbox.day_key(cfg, started_at)
    priority = is_priority(text)
    entry = inbox.format_entry(cfg, started_at, text, priority)
    inbox.append_local(cfg, day, entry)
    drive.enqueue(cfg, day, entry)
    log.info("burst -> %s (%d chars%s)", day, len(text), ", PRIORITY" if priority else "")
    drive.flush(cfg)


def cleanup_clips(cfg: Config) -> None:
    """Transcript is the source of truth; gated clips only live a few days."""
    cutoff = time.time() - cfg.clip_retention_days * 86400
    removed = 0
    for wav in cfg.clips_dir.glob("*/*.wav"):
        if wav.stat().st_mtime < cutoff:
            wav.unlink(missing_ok=True)
            removed += 1
    for day_dir in cfg.clips_dir.iterdir():
        if day_dir.is_dir() and not any(day_dir.iterdir()):
            day_dir.rmdir()
    if removed:
        log.info("cleanup: removed %d expired clips", removed)


def run_daemon() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    cfg = load_config()
    if not cfg.assemblyai_api_key:
        log.error(
            "No AssemblyAI key found (env, ~/.config/office-voice-inbox/.env, "
            "or APIs.md). Bursts will be captured but not transcribed until "
            "a key is available."
        )

    bursts: queue.Queue = queue.Queue()
    capture = CaptureThread(cfg, bursts)
    stop = threading.Event()

    def worker() -> None:
        last_cleanup = 0.0
        last_drive_retry = 0.0
        while not stop.is_set():
            try:
                clip, started_at = bursts.get(timeout=1.0)
            except queue.Empty:
                now = time.monotonic()
                if now - last_drive_retry > DRIVE_RETRY_INTERVAL_S:
                    last_drive_retry = now
                    try:
                        drive.flush(cfg)
                    except Exception as exc:  # noqa: BLE001
                        log.warning("drive retry failed: %s", exc)
                if now - last_cleanup > CLEANUP_INTERVAL_S:
                    last_cleanup = now
                    try:
                        cleanup_clips(cfg)
                    except OSError as exc:
                        log.warning("cleanup failed: %s", exc)
                continue
            try:
                process_burst(cfg, clip, started_at)
            except Exception:  # noqa: BLE001 - one bad burst must not kill the loop
                log.exception("burst processing failed for %s", clip)

    worker_thread = threading.Thread(target=worker, name="worker", daemon=True)

    def shutdown(signum, frame):  # noqa: ARG001
        log.info("shutting down")
        stop.set()
        capture.stop()

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    capture.start()
    worker_thread.start()
    log.info("office voice inbox running (home=%s, drive=%s)", cfg.home, cfg.drive_backend)
    while capture.is_alive():
        capture.join(timeout=1.0)
        if stop.is_set():
            break
    stop.set()
    capture.stop()
    worker_thread.join(timeout=10)
