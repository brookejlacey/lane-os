#!/usr/bin/env bash
# test-lanes.sh - smoke test for the write-lane guard (scripts/hooks/block-cross-lane-write.py).
#
# Proves the PreToolUse guard BLOCKS out-of-lane writes and ALLOWS in-lane ones, so a fork
# can trust the invariant still holds after they edit the guard or rearrange their spine.
# Black-box: feeds the guard its PreToolUse JSON on stdin and checks the exit code
# (0 = allowed, 2 = blocked). No network. It pins LANE_OS_ROOT so spine detection is
# deterministic, and stands up one throwaway git repo in $TMPDIR to play a code lane
# (the guard resolves a code lane with real `git rev-parse`, so a fake path would not do).
set -uo pipefail
cd "$(dirname "$0")/.."
SPINE="$(pwd)"
export LANE_OS_ROOT="$SPINE"
GUARD="$SPINE/scripts/hooks/block-cross-lane-write.py"

CODEREPO="$(mktemp -d)"; git -C "$CODEREPO" init -q
trap 'rm -rf "$CODEREPO"' EXIT
CODE_NAME="$(basename "$CODEREPO")"

pass=0; fail=0
check() { # desc cwd target want_exit
  local desc="$1" cwd="$2" target="$3" want="$4" got
  printf '{"cwd":"%s","tool_input":{"file_path":"%s"}}' "$cwd" "$target" \
    | python3 "$GUARD" >/dev/null 2>&1; got=$?
  if [ "$got" = "$want" ]; then printf '  ok    %s\n' "$desc"; pass=$((pass+1))
  else printf '  FAIL  %s (want exit %s, got %s)\n' "$desc" "$want" "$got"; fail=$((fail+1)); fi
}

echo "== shared drafts inbox (every lane may write) =="
check "spine -> brain/drafts"          "$SPINE"             "$SPINE/brain/drafts/x.md"             0
check "code  -> brain/drafts"          "$CODEREPO"          "$SPINE/brain/drafts/x.md"             0

echo "== spine (workspace-root) lane =="
check "spine -> own brain"             "$SPINE"             "$SPINE/brain/CONCERNS.md"             0
check "spine -> own memory"            "$SPINE"             "$SPINE/memory/foo.md"                 0
check "spine -X external code repo"    "$SPINE"             "/tmp/some-other-repo/app.ts"          2

echo "== code lane =="
check "code  -> own repo"              "$CODEREPO"          "$CODEREPO/src/app.ts"                 0
check "code  -> own projects mirror"   "$CODEREPO"          "$SPINE/projects/$CODE_NAME/STATUS.md" 0
check "code  -X spine memory"          "$CODEREPO"          "$SPINE/memory/foo.md"                 2
check "code  -X a different repo"      "$CODEREPO"          "/tmp/another-repo/x.ts"               2

echo "== desk lane =="
check "desk  -> own desk"              "$SPINE/desks/money" "$SPINE/desks/money/LOG.md"            0
check "desk  -X sibling desk"          "$SPINE/desks/money" "$SPINE/desks/research/LOG.md"         2
check "desk  -X spine brain"           "$SPINE/desks/money" "$SPINE/brain/CONCERNS.md"             2

echo ""
echo "result: $pass passed, $fail failed"
[ "$fail" = 0 ] || exit 1
