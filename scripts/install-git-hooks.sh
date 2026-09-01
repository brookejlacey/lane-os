#!/usr/bin/env bash
# install-git-hooks.sh: wire the drift detector into git itself.
#
# audit-cheap.sh is a self-audit, and a script only runs when something invokes it. With
# no pre-commit hook it runs never, and FAILs ship silently. This installs a pre-commit
# hook that runs `audit-cheap.sh --quiet --staged` in the spine.
#
# `--staged` matters: parallel lane sessions run against ONE checkout. Without it the
# gate read the whole working tree, so another session's half-written file failed THIS
# session's commit. A commit gate judges what is being committed.
#
# .git/hooks/ is not tracked, so re-run this on every fresh clone and machine.
# audit-cheap Check 11 repairs a stale installed hook on its own.
#
# Usage:  bash scripts/install-git-hooks.sh [--dry-run]
set -uo pipefail

SPINE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
DRY=0; [ "${1:-}" = "--dry-run" ] && DRY=1

PRE_COMMIT_BODY='#!/usr/bin/env bash
# AUTO-INSTALLED by scripts/install-git-hooks.sh: runs the drift detector on commit.
REPO_ROOT="$(git rev-parse --show-toplevel)"
if [ -x "$REPO_ROOT/scripts/audit-cheap.sh" ]; then
  bash "$REPO_ROOT/scripts/audit-cheap.sh" --quiet --staged || {
    echo ""
    echo "pre-commit: drift detector FAILED (see above). Fix it, or bypass once with: git commit --no-verify"
    exit 1
  }
fi
'

hp="$(git -C "$SPINE" config --get core.hooksPath 2>/dev/null || true)"
if [ -n "$hp" ]; then
  case "$hp" in /*) hooks="$hp" ;; *) hooks="$SPINE/$hp" ;; esac
else
  hooks="$(git -C "$SPINE" rev-parse --absolute-git-dir)/hooks"
fi

if [ "$DRY" -eq 1 ]; then echo "would install -> $hooks/pre-commit"; exit 0; fi
mkdir -p "$hooks"
printf '%s' "$PRE_COMMIT_BODY" > "$hooks/pre-commit"
chmod +x "$hooks/pre-commit"
echo "installed $hooks/pre-commit (audit-cheap --quiet --staged)"
