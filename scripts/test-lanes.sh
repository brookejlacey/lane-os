#!/usr/bin/env bash
# test-lanes.sh - smoke test for the write-lane guard (scripts/hooks/block-cross-lane-write.py).
#
# Proves the PreToolUse guard BLOCKS out-of-lane writes and ALLOWS in-lane ones, so a
# fork can trust the invariant still holds after they edit the guard or rearrange their spine.
# Black-box: feeds the guard its PreToolUse JSON on stdin and checks the exit code
# (0 = allowed, 2 = blocked). No network. It pins LANE_OS_ROOT so spine detection is
# deterministic, pins LANE_OS_WORKSPACE_ROOTS to a scratch dir, and stands up throwaway
# git repos there to play code lanes (the guard resolves a code lane with real
# `git rev-parse`, so a fake path would not do).
#
# A fail-open guard cannot report its own death, so this test is the only evidence the
# invariant is enforced. audit-cheap runs it on every commit.
set -uo pipefail
cd "$(dirname "$0")/.."
SPINE="$(pwd -P)"
export LANE_OS_ROOT="$SPINE"

WORK="$(mktemp -d)"; trap 'rm -rf "$WORK"' EXIT
export LANE_OS_WORKSPACE_ROOTS="$WORK"
CODEREPO="$WORK/alpha";  mkdir -p "$CODEREPO";  git -C "$CODEREPO" init -q
OTHERREPO="$WORK/beta";  mkdir -p "$OTHERREPO"; git -C "$OTHERREPO" init -q
GUARD="$SPINE/scripts/hooks/block-cross-lane-write.py"
MIRROR="$SPINE/projects/alpha"; mkdir -p "$MIRROR"
trap 'rm -rf "$WORK" "$MIRROR"' EXIT

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
check "desk  -> brain/drafts"          "$SPINE/desks/money" "$SPINE/brain/drafts/x.md"             0

echo "== spine (workspace-root) lane =="
check "spine -> own brain"             "$SPINE"             "$SPINE/brain/CONCERNS.md"             0
check "spine -> own memory"            "$SPINE"             "$SPINE/memory/foo.md"                 0
check "spine -> agent config"          "$SPINE"             "$HOME/.claude/settings.json"          0
check "spine -> machine dotfile"       "$SPINE"             "$HOME/.zshrc"                         0
check "spine -X a code repo"           "$SPINE"             "$CODEREPO/app.ts"                     2

echo "== code lane =="
check "code  -> own repo"              "$CODEREPO"          "$CODEREPO/src/app.ts"                 0
check "code  -> own projects mirror"   "$CODEREPO"          "$SPINE/projects/alpha/STATUS.md"      0
check "code  -> relative path in repo" "$CODEREPO"          "src/app.ts"                           0
check "code  -> scratch in /tmp"       "$CODEREPO"          "/tmp/lane-os-scratch.txt"             0
check "code  -X spine memory"          "$CODEREPO"          "$SPINE/memory/foo.md"                 2
check "code  -X spine brain"           "$CODEREPO"          "$SPINE/brain/CONCERNS.md"             2
check "code  -X another lane's mirror" "$CODEREPO"          "$SPINE/projects/beta/STATUS.md"       2
check "code  -X a different repo"      "$CODEREPO"          "$OTHERREPO/x.ts"                      2

echo "== code lane addressed by its mirror (cwd projects/<name>) =="
check "mirror -> own mirror"           "$MIRROR"            "$MIRROR/STATUS.md"                    0
check "mirror -> own code repo"        "$MIRROR"            "$CODEREPO/src/app.ts"                 0
check "mirror -X spine memory"         "$MIRROR"            "$SPINE/memory/foo.md"                 2
check "mirror -X a different repo"     "$MIRROR"            "$OTHERREPO/x.ts"                      2

echo "== desk lane =="
check "desk  -> own desk"              "$SPINE/desks/money" "$SPINE/desks/money/LOG.md"            0
check "desk  -X sibling desk"          "$SPINE/desks/money" "$SPINE/desks/research/LOG.md"         2
check "desk  -X spine brain"           "$SPINE/desks/money" "$SPINE/brain/CONCERNS.md"             2
check "desk  -X a code repo"           "$SPINE/desks/money" "$CODEREPO/x.ts"                       2

echo "== escape hatch =="
if printf '{"cwd":"%s","tool_input":{"file_path":"%s"}}' "$CODEREPO" "$SPINE/memory/foo.md" \
    | LANE_GUARD_OFF=1 python3 "$GUARD" >/dev/null 2>&1; then
  echo "  ok    LANE_GUARD_OFF=1 disables the guard"; pass=$((pass+1))
else
  echo "  FAIL  LANE_GUARD_OFF=1 did not disable the guard"; fail=$((fail+1))
fi

echo ""
echo "result: $pass passed, $fail failed"
[ "$fail" = 0 ] || exit 1
