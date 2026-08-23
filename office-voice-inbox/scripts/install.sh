#!/bin/bash
# Office Voice Inbox installer (run on the capture Mac, from this directory's parent):
#   cd office-voice-inbox && ./scripts/install.sh
#
# Creates an isolated venv, installs deps, templates + loads the launchd
# agents. Deliberately touches nothing outside this folder, ~/OfficeVoiceInbox,
# ~/.config/office-voice-inbox, ~/Library/LaunchAgents, and ~/Library/Logs —
# safe to run on the Shepherd's Guild iMac without going anywhere near the
# pipeline folder or its .env.

set -euo pipefail

APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
VENV="$APP_DIR/.venv"
AGENTS_DIR="$HOME/Library/LaunchAgents"
UID_NUM="$(id -u)"

echo "==> venv + dependencies (isolated in $VENV)"
python3 -m venv "$VENV"
"$VENV/bin/pip" install --quiet --upgrade pip
"$VENV/bin/pip" install --quiet -r "$APP_DIR/requirements.txt"

mkdir -p "$HOME/Library/Logs" "$AGENTS_DIR" "$HOME/.config/office-voice-inbox"
if [ ! -f "$HOME/.config/office-voice-inbox/.env" ]; then
  cp "$APP_DIR/.env.example" "$HOME/.config/office-voice-inbox/.env"
  echo "==> wrote ~/.config/office-voice-inbox/.env (edit as needed; key can stay in APIs.md)"
fi

echo "==> launchd agents"
for name in com.chrisoswald.office-voice-inbox com.chrisoswald.office-voice-inbox.menubar; do
  sed -e "s|__PYTHON__|$VENV/bin/python|g" \
      -e "s|__WORKDIR__|$APP_DIR|g" \
      -e "s|__HOME__|$HOME|g" \
      "$APP_DIR/launchd/$name.plist" > "$AGENTS_DIR/$name.plist"
  launchctl bootout "gui/$UID_NUM/$name" 2>/dev/null || true
  launchctl bootstrap "gui/$UID_NUM" "$AGENTS_DIR/$name.plist"
done

echo
echo "Installed. Next:"
echo "  1. macOS will ask for Microphone access for Python the first time — allow it."
echo "     (If no prompt appears, run: $VENV/bin/python -m voice_inbox.cli run  once in Terminal.)"
echo "  2. Drive: either 'rclone' backend (existing gdrive remote) or run:"
echo "       $VENV/bin/python -m voice_inbox.cli auth"
echo "  3. Check:  $VENV/bin/python -m voice_inbox.cli status"
echo "  4. Log:    tail -f ~/Library/Logs/office-voice-inbox.log"
