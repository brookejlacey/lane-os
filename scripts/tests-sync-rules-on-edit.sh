#!/usr/bin/env bash
# Proves the rules-sync hook fires on an edit to global/CLAUDE.md and on nothing else.
# Runs the hook from a scratch spine whose scripts/sync-rules.py is a stub that only writes
# a marker, so the real sync never runs and no code lane is touched.
set -u
HERE="$(cd "$(dirname "$0")" && pwd -P)"
T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT
mkdir -p "$T/spine/scripts/hooks" "$T/spine/global"
T="$(cd "$T" && pwd -P)"
cp "$HERE/hooks/sync-rules-on-edit.sh" "$T/spine/scripts/hooks/"
printf 'open("%s/marker", "a").write("ran\\n")\n' "$T" > "$T/spine/scripts/sync-rules.py"
: > "$T/spine/global/CLAUDE.md"
pass=0; fail=0
run() { printf '%s' "$1" | bash "$T/spine/scripts/hooks/sync-rules-on-edit.sh" >/dev/null 2>&1; sleep 1; }
expect() {
  if [[ "$2" == "$3" ]]; then echo "  ok    $1"; pass=$((pass+1)); else echo "  FAIL  $1 (expected $2, got $3)"; fail=$((fail+1)); fi
}
count() { [[ -f "$T/marker" ]] && wc -l < "$T/marker" | tr -d ' ' || echo 0; }

run "{\"tool_name\":\"Edit\",\"tool_input\":{\"file_path\":\"$T/spine/global/CLAUDE.md\"}}"
expect "an Edit to global/CLAUDE.md starts the sync" 1 "$(count)"
run "{\"tool_name\":\"Write\",\"tool_input\":{\"file_path\":\"global/CLAUDE.md\"},\"cwd\":\"$T/spine\"}"
expect "a relative path resolved against cwd starts it too" 2 "$(count)"
run "{\"tool_name\":\"Edit\",\"tool_input\":{\"file_path\":\"$T/spine/CLAUDE.md\"}}"
expect "the spine's own CLAUDE.md does not (the sync never copies it)" 2 "$(count)"
run "{\"tool_name\":\"Edit\",\"tool_input\":{\"file_path\":\"$T/other/global/CLAUDE.md\"}}"
expect "another tree's global/CLAUDE.md does not" 2 "$(count)"
run "not json"
expect "a malformed payload is ignored" 2 "$(count)"

echo ""
if [[ "$fail" -eq 0 ]]; then echo "tests-sync-rules-on-edit: PASS ($pass)"; else echo "tests-sync-rules-on-edit: FAIL ($fail)"; exit 1; fi
