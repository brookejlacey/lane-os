#!/usr/bin/env bash
# Lane OS one-time machine setup. Run from inside your spine repo.
# Idempotent: safe to re-run. Symlinks the constitution + hook, links skills, registers
# every hook in ~/.claude/settings.json, and installs the pre-commit gate in this repo.
set -euo pipefail

SPINE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
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
#    PreToolUse       block-cross-lane-write.py   the write-lane guard
#    Stop             advisory-reply-length.py    measures every reply, silent
#    UserPromptSubmit preflight-reply-length.py   instructs before the next reply, on drift
SETTINGS="$CLAUDE_DIR/settings.json"
python3 - "$SETTINGS" "$SPINE" <<'PY'
import json, os, sys
settings_path, spine = sys.argv[1], sys.argv[2]
s = {}
if os.path.exists(settings_path):
    try:
        s = json.load(open(settings_path))
    except Exception:
        s = {}
hooks = s.setdefault("hooks", {})

def ensure(event, matcher, command, **extra):
    arr = hooks.setdefault(event, [])
    for entry in arr:
        for h in entry.get("hooks", []):
            if h.get("command") == command:
                return
    arr.append({"matcher": matcher, "hooks": [{"type": "command", "command": command, **extra}]})

ensure("SessionStart", "", "bash ~/.claude/hooks/session-start.sh", timeout=30)
ensure("PreToolUse", "Write|Edit|MultiEdit|NotebookEdit", f"python3 {spine}/scripts/hooks/block-cross-lane-write.py")
ensure("Stop", "", f"python3 {spine}/scripts/hooks/advisory-reply-length.py")
ensure("UserPromptSubmit", "", f"python3 {spine}/scripts/hooks/preflight-reply-length.py")
json.dump(s, open(settings_path, "w"), indent=2)
print("updated", settings_path)
PY

# 5. The commit gate: audit-cheap --quiet --staged on every commit in the spine.
bash "$SPINE/scripts/install-git-hooks.sh"

echo
echo "Done. Optionally set LANE_OS_ROOT=$SPINE (and LANE_OS_WORKSPACE_ROOTS=~/repos:~/work)"
echo "in your shell profile so the hooks find the spine and your code lanes from anywhere."
echo "Restart Claude Code to load the hooks."
