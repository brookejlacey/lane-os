#!/usr/bin/env bash
# Lane OS: install always-on `claude remote-control` hosts, one per lane, so you can
# drive real (non-sandbox) sessions on this machine from your phone or another laptop.
# macOS / launchd. RUN ON THE ALWAYS-ON HOST.
#
# Each host is a KeepAlive LaunchAgent running `claude remote-control --name <display>`
# with WorkingDirectory set to that lane, so connecting drops you into a correctly
# scoped session (the SessionStart hook + write-lane guard apply automatically).
# Idempotent: re-running regenerates and reloads each agent.

set -uo pipefail

# --- EDIT THIS: one line per lane you want reachable -------------------------
# format:  shortname : phone-display-name : absolute working directory
# Point these at your real spine, code repos, and desks on THIS machine.
SPINE="${LANE_OS_ROOT:-$HOME/work/spine}"
HOSTS=(
  "spine:my-spine:$SPINE"
  # "app:my-app:$HOME/work/my-app"
  # "planning:my-planning:$SPINE/desks/planning"
)
# ----------------------------------------------------------------------------

CLAUDE_BIN="$(command -v claude || echo "$HOME/.local/bin/claude")"
LA="$HOME/Library/LaunchAgents"
LOGS="$HOME/Library/Logs/claude-remote"
# Bake a sane PATH into the agents (launchd starts with a minimal one).
PATHVAL="$HOME/.local/bin:/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

[ -x "$CLAUDE_BIN" ] || { echo "claude CLI not found (looked at: $CLAUDE_BIN)"; exit 1; }
mkdir -p "$LA" "$LOGS"
uid=$(id -u)

for entry in "${HOSTS[@]}"; do
  short="${entry%%:*}"; rest="${entry#*:}"; name="${rest%%:*}"; wd="${rest#*:}"
  if [ ! -d "$wd" ]; then
    echo "SKIP $name -- working dir missing: $wd"; continue
  fi
  label="com.lane-os.remote-$short"
  plist="$LA/$label.plist"
  cat > "$plist" <<PL
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$label</string>
  <key>ProgramArguments</key>
  <array>
    <string>$CLAUDE_BIN</string>
    <string>remote-control</string>
    <string>--name</string>
    <string>$name</string>
  </array>
  <key>WorkingDirectory</key><string>$wd</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key><string>$PATHVAL</string>
    <key>HOME</key><string>$HOME</string>
    <key>LANE_OS_ROOT</key><string>$SPINE</string>
  </dict>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>ThrottleInterval</key><integer>10</integer>
  <key>StandardOutPath</key><string>$LOGS/$short-out.log</string>
  <key>StandardErrorPath</key><string>$LOGS/$short-err.log</string>
</dict>
</plist>
PL
  launchctl bootout "gui/$uid/$label" 2>/dev/null || true
  if launchctl bootstrap "gui/$uid" "$plist" 2>/dev/null; then
    echo "loaded $name  ($wd)"
  else
    launchctl load "$plist" 2>/dev/null && echo "loaded $name (load) ($wd)" || echo "FAILED $name"
  fi
done

echo
echo "Verify:   launchctl list | grep lane-os.remote"
echo "Logs:     $LOGS/"
echo "Restart one:  launchctl kickstart -k gui/$uid/com.lane-os.remote-<short>"
echo "Remove one:   launchctl bootout gui/$uid/com.lane-os.remote-<short>"
echo
echo "If a host crash-loops with a 401 'only available with claude.ai subscriptions',"
echo "run 'claude auth login' on THIS machine (see docs/code-from-anywhere.md)."
