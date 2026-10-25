#!/bin/sh
# Install the weekly scan-only launchd job for the current user.
# Usage: launchd/install.sh          (install or reinstall)
#        launchd/install.sh remove   (uninstall)
set -eu

HERE=$(cd "$(dirname "$0")/.." && pwd)
LABEL=com.devsweep.scan
DEST="$HOME/Library/LaunchAgents/$LABEL.plist"
UID_=$(id -u)

if [ "${1:-}" = "remove" ]; then
  launchctl bootout "gui/$UID_/$LABEL" 2>/dev/null || true
  rm -f "$DEST"
  echo "removed $LABEL"
  exit 0
fi

mkdir -p "$HOME/Library/LaunchAgents" "$HOME/.devsweep/logs"
sed -e "s|__DEVSWEEP__|$HERE|g" -e "s|__HOME__|$HOME|g" "$HERE/launchd/$LABEL.plist" > "$DEST"
plutil -lint "$DEST"
launchctl bootout "gui/$UID_/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$UID_" "$DEST"
launchctl print "gui/$UID_/$LABEL" | grep -E 'state|program' | head -3
echo "installed $LABEL: scan every Monday 09:00, log in ~/.devsweep/logs/scan.log"
echo "run now:  launchctl kickstart gui/$UID_/$LABEL"
