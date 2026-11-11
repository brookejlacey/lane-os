#!/usr/bin/env bash
# PostToolUse: after a write that lands in the spine's global/CLAUDE.md, run the rules sync.
#
# "After any edit to the constitution, run the sync" was a rule held in prose, and a rule
# held in prose is run from memory: code lanes worked to rules a day stale. The sync already
# defers the commit in a repo with a live session and never writes a repo an outside reader
# sees, so running it here is safe. It runs detached so the turn is not held, and logs to
# outputs/rules-sync.log.
#
# Sees Write, Edit, MultiEdit and NotebookEdit (their file_path). A shell command that writes
# the file is not seen; run scripts/sync-rules.py by hand after one.
payload="$(cat)"
ROOT="$(cd "$(dirname "$0")/../.." && pwd -P)"
target="$(printf '%s' "$payload" | python3 -c '
import json, os, sys
root = sys.argv[1]
try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(0)
ti = d.get("tool_input") or {}
fp = ti.get("file_path") or ti.get("notebook_path")
if not isinstance(fp, str):
    sys.exit(0)
if not os.path.isabs(fp):
    fp = os.path.join(d.get("cwd") or os.getcwd(), fp)
if os.path.realpath(fp) == os.path.join(root, "global", "CLAUDE.md"):
    print(fp)
' "$ROOT")"
[ -n "$target" ] || exit 0
[ -f "$ROOT/scripts/sync-rules.py" ] || exit 0
mkdir -p "$ROOT/outputs"
( cd "$ROOT" && nohup python3 scripts/sync-rules.py >> "$ROOT/outputs/rules-sync.log" 2>&1 & ) >/dev/null 2>&1
echo "rules sync started in the background for $target (outputs/rules-sync.log)" >&2
exit 0
