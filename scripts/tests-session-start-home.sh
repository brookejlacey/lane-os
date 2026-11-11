#!/usr/bin/env bash
# Proves hooks/session-start.sh touches ~/.claude only when its spine is the installed one.
# Every case runs under a temp HOME against a scratch spine, so the real ~/.claude and the
# real spine are never read or written.
set -u
for v in $(env | sed -n 's/^\(GIT_[A-Za-z_]*\)=.*/\1/p'); do unset "$v"; done
HOOK="$(cd "$(dirname "$0")/.." && pwd -P)/hooks/session-start.sh"
T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT
T="$(cd "$T" && pwd -P)"
mkspine() {  # a minimal spine: one skill, the constitution, a git dir
  mkdir -p "$1/global" "$1/skills/alpha" "$1/brain/drafts"
  echo "# rules" > "$1/global/CLAUDE.md"; echo "# alpha" > "$1/skills/alpha/SKILL.md"
  git -C "$1" init -q
}
mkspine "$T/spine"; mkspine "$T/other"
pass=0; fail=0
expect() { if [[ "$2" == "$3" ]]; then echo "  ok    $1"; pass=$((pass+1)); else echo "  FAIL  $1 (expected $2, got $3)"; fail=$((fail+1)); fi; }
run() { (cd "$T" && HOME="$1" LANE_OS_ROOT="$T/spine" bash "$HOOK" >"$1/out" 2>&1); }

# 1. Nothing installed: no ~/.claude is created, and the hook says why.
H="$T/h1"; mkdir -p "$H"; run "$H"
expect "no install: ~/.claude/skills is not created" no "$([[ -e $H/.claude/skills ]] && echo yes || echo no)"
expect "no install: the NOTE says ~/.claude was left alone" yes "$(grep -q 'left alone' "$H/out" && echo yes || echo no)"

# 2. Installed here: the skill is linked.
H="$T/h2"; mkdir -p "$H/.claude"; ln -s "$T/spine/global/CLAUDE.md" "$H/.claude/CLAUDE.md"; run "$H"
expect "installed here: the skill is linked into ~/.claude/skills" "$T/spine/skills/alpha" "$(readlink "$H/.claude/skills/alpha")"
expect "installed here: no NOTE" no "$(grep -q 'left alone' "$H/out" && echo yes || echo no)"

# 3. Another spine is installed: its links stay exactly as they were.
H="$T/h3"; mkdir -p "$H/.claude/skills"; ln -s "$T/other/global/CLAUDE.md" "$H/.claude/CLAUDE.md"
ln -s "$T/other/skills/alpha" "$H/.claude/skills/alpha"; run "$H"
expect "another spine installed: its skill link is untouched" "$T/other/skills/alpha" "$(readlink "$H/.claude/skills/alpha")"
expect "another spine installed: its CLAUDE.md link is untouched" "$T/other/global/CLAUDE.md" "$(readlink "$H/.claude/CLAUDE.md")"

# 4. A plain ~/.claude/CLAUDE.md the human wrote is never overwritten.
H="$T/h4"; mkdir -p "$H/.claude"; echo "mine" > "$H/.claude/CLAUDE.md"; run "$H"
expect "a plain CLAUDE.md is never overwritten" mine "$(cat "$H/.claude/CLAUDE.md")"

# 5. Installed here, but a real directory sits where a skill link would go: it survives.
H="$T/h5"; mkdir -p "$H/.claude/skills/alpha"; echo keep > "$H/.claude/skills/alpha/SKILL.md"
ln -s "$T/spine/global/CLAUDE.md" "$H/.claude/CLAUDE.md"; run "$H"
expect "a real skill directory is never deleted" keep "$(cat "$H/.claude/skills/alpha/SKILL.md" 2>/dev/null)"

echo ""
if [[ "$fail" -eq 0 ]]; then echo "tests-session-start-home: PASS ($pass)"; else echo "tests-session-start-home: FAIL ($fail)"; exit 1; fi
