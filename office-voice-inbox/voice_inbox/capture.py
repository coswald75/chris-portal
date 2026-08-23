"""Mic capture with voice-activity gating.

16 kHz mono int16 from the mic, chopped into 30 ms frames for webrtcvad.
Silence is dropped on the floor — it never touches disk. Voiced audio is
buffered into "bursts"; each burst is written as one small WAV clip and
handed to the transcription queue.

Burst rules:
  - starts when ~75% of a 300 ms window is voiced (with the window as pre-roll)
  - ends after BURST_END_SILENCE_MS of hush
  - dropped entirely if it carried less than MIN_VOICED_MS of speech
    (keyboard clatter, door thumps)
  - force-split at MAX_BURST_SECONDS so a long ramble still lands "nearly now"
"""

import collections
import logging
import queue
import threading
import wave
from datetime import datetime, timezone
from pathlib import Path

from .config import Config
from . import state as state_mod

log = logging.getLogger("voice_inbox.capture")

SAMPLE_RATE = 16000
FRAME_MS = 30
FRAME_SAMPLES = SAMPLE_RATE * FRAME_MS // 1000  # 480
FRAME_BYTES = FRAME_SAMPLES * 2  # int16 mono

TRIGGER_WINDOW_FRAMES = 10  # 300 ms
TRIGGER_RATIO = 0.75


class Burst:
    def __init__(self, started_at: datetime, preroll: list[bytes]):
        self.started_at = started_at
        self.frames: list[bytes] = list(preroll)
        self.voiced_ms = 0
        self.silence_ms = 0

    @property
    def duration_s(self) -> float:
        return len(self.frames) * FRAME_MS / 1000.0


class Segmenter:
    """Feed 30 ms frames in; completed bursts come out via the callback."""

    def __init__(self, cfg: Config, on_burst):
        import webrtcvad

        self.cfg = cfg
        self.on_burst = on_burst
        self.vad = webrtcvad.Vad(cfg.vad_aggressiveness)
        self.window = collections.deque(maxlen=TRIGGER_WINDOW_FRAMES)
        self.burst: Burst | None = None

    def reset(self) -> None:
        self.window.clear()
        if self.burst is not None:
            self._finish()

    def feed(self, frame: bytes) -> None:
        voiced = self.vad.is_speech(frame, SAMPLE_RATE)
        self.window.append((frame, voiced))

        if self.burst is None:
            if len(self.window) == self.window.maxlen:
                voiced_count = sum(1 for _, v in self.window if v)
                if voiced_count >= TRIGGER_RATIO * self.window.maxlen:
                    preroll = [f for f, _ in self.window]
                    self.burst = Burst(datetime.now(timezone.utc), preroll)
                    self.burst.voiced_ms = voiced_count * FRAME_MS
                    self.window.clear()
            return

        self.burst.frames.append(frame)
        if voiced:
            self.burst.voiced_ms += FRAME_MS
            self.burst.silence_ms = 0
        else:
            self.burst.silence_ms += FRAME_MS

        if (
            self.burst.silence_ms >= self.cfg.burst_end_silence_ms
            or self.burst.duration_s >= self.cfg.max_burst_seconds
        ):
            self._finish()

    def _finish(self) -> None:
        burst, self.burst = self.burst, None
        if burst is None:
            return
        # Trim the trailing hush; keep ~300 ms tail.
        tail_keep = 10
        trailing = min(burst.silence_ms // FRAME_MS, len(burst.frames))
        if trailing > tail_keep:
            burst.frames = burst.frames[: len(burst.frames) - (trailing - tail_keep)]
        if burst.voiced_ms < self.cfg.min_voiced_ms:
            log.debug("dropped %dms non-speech blip", burst.voiced_ms)
            return
        self.on_burst(burst)


def write_clip(cfg: Config, burst: Burst) -> Path:
    from .inbox import day_key, to_local

    day = day_key(cfg, burst.started_at)
    day_dir = cfg.clips_dir / day
    day_dir.mkdir(parents=True, exist_ok=True)
    stamp = to_local(cfg, burst.started_at).strftime("%H%M%S")
    path = day_dir / f"{stamp}.wav"
    n = 1
    while path.exists():
        path = day_dir / f"{stamp}-{n}.wav"
        n += 1
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(SAMPLE_RATE)
        wav.writeframes(b"".join(burst.frames))
    return path


def resolve_device(name_or_index: str):
    if not name_or_index:
        return None
    import sounddevice as sd

    try:
        return int(name_or_index)
    except ValueError:
        pass
    needle = name_or_index.lower()
    for idx, dev in enumerate(sd.query_devices()):
        if dev["max_input_channels"] > 0 and needle in dev["name"].lower():
            return idx
    raise RuntimeError(f"No input device matching {name_or_index!r}")


class CaptureThread(threading.Thread):
    """Owns the mic stream. Honors the on/off/mute state file: while off or
    muted, frames are discarded before VAD and any open burst is flushed."""

    def __init__(self, cfg: Config, burst_queue: queue.Queue):
        super().__init__(name="capture", daemon=True)
        self.cfg = cfg
        self.burst_queue = burst_queue
        self.stop_event = threading.Event()
        self._raw = queue.Queue(maxsize=256)

    def _on_burst(self, burst: Burst) -> None:
        path = write_clip(self.cfg, burst)
        log.info(
            "burst %.1fs (%.0fs voiced) -> %s",
            burst.duration_s,
            burst.voiced_ms / 1000,
            path.name,
        )
        self.burst_queue.put((path, burst.started_at))

    def run(self) -> None:
        import sounddevice as sd

        segmenter = Segmenter(self.cfg, self._on_burst)
        pending = b""
        was_capturing = True

        def callback(indata, frames, time_info, status):
            if status:
                log.warning("audio status: %s", status)
            try:
                self._raw.put_nowait(bytes(indata))
            except queue.Full:
                pass  # transcription is behind; drop rather than block CoreAudio

        with sd.RawInputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="int16",
            blocksize=FRAME_SAMPLES,
            device=resolve_device(self.cfg.input_device),
            callback=callback,
        ):
            log.info("mic open (16 kHz mono, VAD level %d)", self.cfg.vad_aggressiveness)
            while not self.stop_event.is_set():
                try:
                    chunk = self._raw.get(timeout=0.5)
                except queue.Empty:
                    continue
                capturing = state_mod.is_capturing(self.cfg.state_file)
                if not capturing:
                    if was_capturing:
                        segmenter.reset()  # flush any open burst, then go quiet
                        pending = b""
                        log.info("capture paused (off/muted)")
                    was_capturing = False
                    continue
                if not was_capturing:
                    log.info("capture resumed")
                was_capturing = True

                pending += chunk
                while len(pending) >= FRAME_BYTES:
                    segmenter.feed(pending[:FRAME_BYTES])
                    pending = pending[FRAME_BYTES:]
        segmenter.reset()

    def stop(self) -> None:
        self.stop_event.set()
