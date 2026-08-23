# Office Voice Inbox

A stream-of-consciousness voice inbox for Chris's private office. The mic
stays open while the office session is on. Speech bursts are gated by VAD,
transcribed by AssemblyAI, and appended — verbatim, within a minute or two —
to one Google Doc per day in the Drive folder **Office Voice Inbox**, where
Kyle reads them. Silence never touches disk. This is a dump, not a
secretary: no cleanup of diction, no summaries, no talk-back.

Spec locked 2026-08-22 (Kyle + Chris). This folder contains code only — no
keys, no tokens, ever.

## Which Mac

**macOS only, by design.** Any Mac in the office works. Prefer a Mac that is
*not* the Shepherd's Guild pipeline iMac; if the iMac is the only machine in
that room, this is safe to run there — it is fully isolated (own folder, own
venv `office-voice-inbox/.venv`, own launchd labels
`com.chrisoswald.office-voice-inbox*`) and never touches the pipeline folder
or its `.env`.

(An iPad/iOS version was considered and parked: iOS suspends background mic
apps, which is exactly wrong for an always-open office mic. Possible v3 if
ever needed.)

## Install (on the capture Mac)

```bash
git clone <this repo> && cd chris-portal/office-voice-inbox
./scripts/install.sh
```

Then:

1. **Mic permission** — macOS prompts for Microphone access for Python the
   first time audio opens. If no prompt appears, run once in Terminal:
   `.venv/bin/python -m voice_inbox.cli run` (Ctrl-C after the prompt).
2. **AssemblyAI key** — nothing to do if the key lives in the Obsidian note
   `~/Desktop/Macbook Air/APIs.md` on a line mentioning AssemblyAI; the
   daemon reads it from there. Otherwise put `ASSEMBLYAI_API_KEY=...` in
   `~/.config/office-voice-inbox/.env`. Never commit it; the code never
   prints it.
3. **Drive** — pick one in `~/.config/office-voice-inbox/.env`:
   - `DRIVE_BACKEND=docs` (default): real Google Docs, one per day. One-time
     setup: drop an OAuth *Desktop app* client JSON (Drive API + Docs API
     enabled) at `~/.config/office-voice-inbox/credentials.json`, then run
     `.venv/bin/python -m voice_inbox.cli auth` and sign in as
     chris@sovgracekc.org. The app creates the "Office Voice Inbox" folder
     itself (scope is `drive.file` — it can only see files it created).
   - `DRIVE_BACKEND=rclone`: if the Mac already has an rclone gdrive remote,
     the daily markdown file is synced into the Drive folder instead. Same
     shape, zero Google-API setup. Set `RCLONE_REMOTE` to the remote name.
4. **Check** — `.venv/bin/python -m voice_inbox.cli status`

## Daily use

- Menu bar: 🎙 capturing · 🔇 muted · ⏸ session off. Toggles are also on the
  CLI: `on / off / mute / unmute`. Hardware mute always wins if the mic has one.
- Say **"Kyle"**, **"Kyle note"**, **"that's a task"**, or **"put that on
  the list"** anywhere in a burst and it gets a `[PRIORITY]` line under its
  heading so Kyle sees it first. Exactly those cues, case-insensitive.
- Each burst lands in the day's doc (`YYYY-MM-DD Office Voice Inbox`) as:

  ```
  ## HH:MM CT
  [PRIORITY]        <- only when a cue fired
  transcript text
  ```

- If Drive is unreachable, bursts queue locally and retry every minute; the
  local markdown copy in `~/OfficeVoiceInbox/inbox/` is always written first
  and is the fallback of record.

## Disk & privacy

- Raw always-on audio is **never** stored. VAD drops the hush; only voiced
  bursts are written as small WAV clips (≈60 min of speech ≈ 15–30 MB/day —
  verify with `voice-inbox stats`). Clips auto-delete after
  `CLIP_RETENTION_DAYS` (default 3); the transcript is the source of truth.
- AssemblyAI transcripts are deleted upstream immediately after the text
  comes back.
- If a pastoral conversation ever wanders in: delete that burst's section
  from the day's doc (and local `.md`), and its clip from
  `~/OfficeVoiceInbox/clips/YYYY-MM-DD/` if still inside the retention window.
- Nothing is emailed, Slacked, or posted anywhere. Drive folder + local disk
  only.

## Verifying the build order (spec §12)

```bash
V=.venv/bin/python
$V -m voice_inbox.cli devices          # pick INPUT_DEVICE if not default
$V -m voice_inbox.cli run              # talk for a minute, Ctrl-C
$V -m voice_inbox.cli stats            # clips stay in the tens of MB
$V -m voice_inbox.cli transcribe-one ~/OfficeVoiceInbox/clips/<day>/<clip>.wav
$V -m voice_inbox.cli status           # pending Drive appends should be 0
tail -f ~/Library/Logs/office-voice-inbox.log
```

Unit tests (no mic or network needed): `python3 -m unittest discover tests`

## Layout

```
voice_inbox/
  capture.py     mic -> 30ms frames -> webrtcvad gate -> burst WAV clips
  transcribe.py  AssemblyAI async REST per clip; deletes transcript upstream
  priority.py    the four cues, nothing more
  inbox.py       CT day keys, entry shape, local daily markdown
  drive.py       docs / rclone backends + pending retry queue
  daemon.py      capture thread + worker + clip cleanup
  cli.py         run/on/off/mute/status/auth/devices/stats/transcribe-one
  menubar.py     rumps toggle (writes the shared state file only)
launchd/         agent templates (installer fills in paths)
scripts/         install.sh / uninstall.sh
```

Out of scope until Chris says so: Supabase mirror (v2), Todoist auto-tasks,
summaries, any web UI or companion layer.
