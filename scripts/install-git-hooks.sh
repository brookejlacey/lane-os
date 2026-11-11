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
# The same body is installed as pre-merge-commit, because git skips pre-commit on a
# merge: lines a merge brings in (a worktree branch, a teammate's branch) were never
# checked. A conflicted merge is finished with `git commit`, which runs pre-commit.
#
# A MISSING CHECKER REFUSES THE COMMIT. The hook used to run audit-cheap only when it was
# present and executable, and pass silently otherwise, so a deleted or un-executable
# checker looked exactly like a clean commit. AUDIT_CHEAP_SKIP=1 is the one bypass and it
# skips only this checker; --no-verify skips every hook the repo has.
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
# Installed as pre-commit and as pre-merge-commit (git skips pre-commit on a merge).
# AUDIT_CHEAP_SKIP=1 skips ONLY this detector; every other hook still runs.
HOOK="$(basename "$0")"
if [ "${AUDIT_CHEAP_SKIP:-0}" = "1" ]; then
  echo "$HOOK: drift detector skipped (AUDIT_CHEAP_SKIP=1); every other hook still runs" >&2
  exit 0
fi
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"
[ -n "$REPO_ROOT" ] || REPO_ROOT="$(pwd -P)"
AUDIT="$REPO_ROOT/scripts/audit-cheap.sh"
if [ ! -f "$AUDIT" ] || [ ! -x "$AUDIT" ]; then
  echo "$HOOK: drift detector missing or not executable: $AUDIT" >&2
  echo "$HOOK: this hook exists to run it, so the commit is refused rather than passed unchecked." >&2
  echo "$HOOK: restore it (git checkout -- scripts/audit-cheap.sh; chmod +x scripts/audit-cheap.sh), or skip only the detector with: AUDIT_CHEAP_SKIP=1 git commit ..." >&2
  exit 1
fi
bash "$AUDIT" --quiet --staged || {
  echo ""
  echo "$HOOK: drift detector FAILED (see above). Fix it. If a check is wrong, skip only the detector with: AUDIT_CHEAP_SKIP=1 git commit ..."
  exit 1
}
'

hp="$(git -C "$SPINE" config --get core.hooksPath 2>/dev/null || true)"
if [ -n "$hp" ]; then
  case "$hp" in /*) hooks="$hp" ;; *) hooks="$SPINE/$hp" ;; esac
else
  hooks="$(git -C "$SPINE" rev-parse --absolute-git-dir)/hooks"
fi

if [ "$DRY" -eq 1 ]; then echo "would install -> $hooks/pre-commit and $hooks/pre-merge-commit"; exit 0; fi
mkdir -p "$hooks"
for h in pre-commit pre-merge-commit; do
  printf '%s' "$PRE_COMMIT_BODY" > "$hooks/$h"
  chmod +x "$hooks/$h"
done
echo "installed $hooks/pre-commit and $hooks/pre-merge-commit (audit-cheap --quiet --staged)"
