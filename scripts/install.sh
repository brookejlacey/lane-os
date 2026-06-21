#!/usr/bin/env bash
# Lane OS one-time machine setup. Run from inside your spine repo.
# Idempotent: safe to re-run. Symlinks the constitution + hook, links skills,
# and registers the SessionStart + PreToolUse hooks in ~/.claude/settings.json.
set -euo pipefail

SPINE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CLAUDE_DIR="$HOME/.claude"
mkdir -p "$CLAUDE_DIR/hooks" "$CLAUDE_DIR/skills"

echo "Spine repo: $SPINE"

# 1. Symlink the constitution so every session loads it.
ln -sfn "$SPINE/global/CLAUDE.md" "$CLAUDE_DIR/CLAUDE.md"
echo "linked ~/.claude/CLAUDE.md"

# 2. Symlink the SessionStart hook.
ln -sfn "$SPINE/hooks/session-start.sh" "$CLAUDE_DIR/hooks/session-start.sh"
chmod +x "$SPINE/hooks/session-start.sh"
echo "linked ~/.claude/hooks/session-start.sh"

# 3. Symlink every skill.
for d in "$SPINE/skills"/*/; do
  [ -d "$d" ] || continue
  ln -sfn "${d%/}" "$CLAUDE_DIR/skills/$(basename "$d")"
done
echo "linked skills"

# 4. Register the hooks in settings.json (merge, do not clobber).
SETTINGS="$CLAUDE_DIR/settings.json"
GUARD="$SPINE/scripts/hooks/block-cross-lane-write.py"
python3 - "$SETTINGS" "$SPINE/hooks/session-start.sh" "$GUARD" <<'PY'
import json, os, sys
settings_path, hook, guard = sys.argv[1], sys.argv[2], sys.argv[3]
s = {}
if os.path.exists(settings_path):
    try:
        s = json.load(open(settings_path))
    except Exception:
        s = {}
hooks = s.setdefault("hooks", {})

def ensure(event, matcher, command):
    arr = hooks.setdefault(event, [])
    for entry in arr:
        for h in entry.get("hooks", []):
            if h.get("command") == command:
                return
    arr.append({"matcher": matcher, "hooks": [{"type": "command", "command": command}]})

ensure("SessionStart", "", "bash ~/.claude/hooks/session-start.sh")
ensure("PreToolUse", "Write|Edit|MultiEdit|NotebookEdit", "python3 " + guard)
json.dump(s, open(settings_path, "w"), indent=2)
print("updated", settings_path)
PY

echo
echo "Done. Optionally set LANE_OS_ROOT=$SPINE in your shell profile so the hooks"
echo "find the spine even from unusual locations. Restart Claude Code to load the hooks."
