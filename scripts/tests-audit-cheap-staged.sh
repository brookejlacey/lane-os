#!/usr/bin/env bash
# Asserts that --staged scopes the changed-file checks to the index, and still BLOCKS.
#
# Parallel lane sessions share one checkout. Before --staged, every changed-file check
# read the whole working tree, so a half-written file in one lane failed the pre-commit
# gate for a commit in another lane, and that session bypassed the gate with --no-verify
# over a defect it did not write. A scoping change that only narrows is worthless if it
# narrows to nothing, so this asserts BOTH directions: the foreign unstaged file is
# ignored, and the SAME file staged still fails the commit.
#
# The planted defect is a credential shape (Check 15), the one check that runs in any repo.
set -uo pipefail

# This test builds a scratch repo and stages files in it, but it runs from the PRE-COMMIT
# HOOK, which exports GIT_INDEX_FILE (and friends) pointing at the REAL repo. Without this
# every `git add` below would stage into the real index. Nothing here may inherit a git path.
unset GIT_INDEX_FILE GIT_DIR GIT_WORK_TREE GIT_OBJECT_DIRECTORY \
      GIT_ALTERNATE_OBJECT_DIRECTORIES GIT_PREFIX GIT_COMMON_DIR

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
AUDIT="$HERE/audit-cheap.sh"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
fails=0
check() { if [[ "$3" == "$2" ]]; then echo "  ok    $1"; else echo "  FAIL  $1 (expected $2, got $3)"; fails=$((fails+1)); fi; }

REPO="$TMP/lane-repo"; mkdir -p "$REPO"
git -C "$REPO" init -q
git -C "$REPO" config user.email test@example.invalid
git -C "$REPO" config user.name test
git -C "$REPO" config commit.gpgsign false
echo "baseline" > "$REPO/README.md"
git -C "$REPO" add README.md
git -C "$REPO" -c core.hooksPath=/dev/null commit -qm baseline

# A file from ANOTHER lane, mid-edit and never staged, carrying a planted key shape.
printf 'notes\ntoken = "ghp_%s"\n' "$(printf 'A%.0s' $(seq 1 36))" > "$REPO/other-lane-notes.md"
# This lane's own change, clean and staged.
echo "my lane" > "$REPO/my-lane-status.md"
git -C "$REPO" add my-lane-status.md

run() { AUDIT_CHEAP_SELFTEST=1 bash "$AUDIT" --repo "$REPO" --quiet "$@" >/dev/null 2>&1; echo $?; }

check "the wide view sees the foreign unstaged defect"          1 "$(run)"
check "--staged ignores the foreign unstaged file"              0 "$(run --staged)"
git -C "$REPO" add other-lane-notes.md
check "--staged still blocks the same file once it is staged"   1 "$(run --staged)"
git -C "$REPO" reset -q other-lane-notes.md
check "unstaging it clears the staged view again"               0 "$(run --staged)"

echo "tests-audit-cheap-staged: $([[ $fails -eq 0 ]] && echo PASS || echo "FAIL ($fails)")"
exit "$fails"
