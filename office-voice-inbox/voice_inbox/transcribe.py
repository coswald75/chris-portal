"""AssemblyAI transcription for one burst clip.

Uses the plain REST API (upload + async transcript) — simplest and cheapest
for bursty office speech; no streaming session to babysit. The transcript
object is deleted from AssemblyAI right after the text comes back, so
nothing lingers in the cloud beyond what was needed to transcribe.

The words come back as spoken. No summarization, no rewriting.
"""

import logging
import time
from pathlib import Path

import requests

log = logging.getLogger("voice_inbox.transcribe")

BASE = "https://api.assemblyai.com/v2"
POLL_INTERVAL_S = 2
POLL_TIMEOUT_S = 300


class TranscriptionError(RuntimeError):
    pass


def transcribe_clip(api_key: str, clip: Path) -> str:
    """Upload one WAV clip, wait for the transcript, delete it upstream,
    return the text ('' if AssemblyAI heard no words)."""
    if not api_key:
        raise TranscriptionError(
            "No AssemblyAI API key. Set ASSEMBLYAI_API_KEY in "
            "~/.config/office-voice-inbox/.env or keep it in APIs.md."
        )
    headers = {"authorization": api_key}

    with open(clip, "rb") as fh:
        resp = requests.post(f"{BASE}/upload", headers=headers, data=fh, timeout=120)
    resp.raise_for_status()
    upload_url = resp.json()["upload_url"]

    resp = requests.post(
        f"{BASE}/transcript",
        headers=headers,
        json={
            "audio_url": upload_url,
            "punctuate": True,
            "format_text": True,
        },
        timeout=30,
    )
    resp.raise_for_status()
    transcript_id = resp.json()["id"]

    deadline = time.monotonic() + POLL_TIMEOUT_S
    try:
        while True:
            resp = requests.get(
                f"{BASE}/transcript/{transcript_id}", headers=headers, timeout=30
            )
            resp.raise_for_status()
            data = resp.json()
            status = data["status"]
            if status == "completed":
                return (data.get("text") or "").strip()
            if status == "error":
                raise TranscriptionError(data.get("error", "transcription failed"))
            if time.monotonic() > deadline:
                raise TranscriptionError("timed out waiting for transcript")
            time.sleep(POLL_INTERVAL_S)
    finally:
        try:
            requests.delete(
                f"{BASE}/transcript/{transcript_id}", headers=headers, timeout=30
            )
        except requests.RequestException:
            log.warning("could not delete transcript %s upstream", transcript_id)
