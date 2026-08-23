#!/bin/bash
# Stop and remove the launchd agents. Leaves ~/OfficeVoiceInbox (transcripts,
# clips) and ~/.config/office-voice-inbox alone — delete those by hand if done.

set -uo pipefail

UID_NUM="$(id -u)"
for name in com.chrisoswald.office-voice-inbox com.chrisoswald.office-voice-inbox.menubar; do
  launchctl bootout "gui/$UID_NUM/$name" 2>/dev/null || true
  rm -f "$HOME/Library/LaunchAgents/$name.plist"
done
echo "Agents removed. Data left in ~/OfficeVoiceInbox."
