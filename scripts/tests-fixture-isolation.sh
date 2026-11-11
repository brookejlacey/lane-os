#!/usr/bin/env bash
# Asserts that no test in scripts/ can write into the repo whose commit is running it.
#
# The tests run from the pre-commit gate. Inside a hook git exports GIT_INDEX_FILE, and
# in a linked worktree GIT_DIR too, both pointing at the LIVE repo. A test that builds a
# scratch repo and inherits them runs its `git init`, `add` and `commit` against the live
# repo instead: a fixture committed over a real branch is how this class of bug shows up.
# Every test that runs git must drop every GIT_* variable before its first git call.
#
# This runs each test (test-lanes.sh, tests-*.sh, tests-*.py, except itself) twice
# against a decoy repo that stands in for the live one, and asserts the decoy is byte for
# byte unchanged afterwards:
#
#   A. with GIT_DIR, GIT_INDEX_FILE and GIT_WORK_TREE exported at the decoy
#   B. from inside a REAL pre-commit hook, on a commit made in a linked worktree of the
#      decoy, so git itself sets the variables the way it does for the real gate
#
# and that each test exits the same way it does in a clean environment.
#
# Run: bash scripts/tests-fixture-isolation.sh
set -uo pipefail
for _v in $(compgen -e); do case "$_v" in GIT_*) unset "$_v" ;; esac; done

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
SELF="$(basename "${BASH_SOURCE[0]}")"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
# The tests run here with a scratch HOME, so nothing they start can reach the real
# ~/.claude (its settings, its skills links, its sessions) or the real git config.
export HOME="$TMP/home"; mkdir -p "$HOME"
fails=0
ok()  { echo "  ok    $1"; }
bad() { echo "  FAIL  $1"; fails=$((fails + 1)); }

DECOY="$TMP/decoy"; WT="$TMP/decoy-wt"
git init -q "$DECOY"
git -C "$DECOY" config user.email test@example.invalid
git -C "$DECOY" config user.name test
git -C "$DECOY" config commit.gpgsign false
echo "the live repo" > "$DECOY/README.md"
git -C "$DECOY" add README.md
git -C "$DECOY" commit -q -m "live history"
git -C "$DECOY" worktree add -q -b lane "$WT"
echo "a lane's real change" > "$WT/lane-change.md"
git -C "$WT" add lane-change.md

# The hook runs whatever $TMP/hook-cmd names, records its exit, and always refuses, so
# the decoy commit itself never lands and the only thing that could change the decoy is
# the test.
cat > "$DECOY/.git/hooks/pre-commit" <<HOOK
#!/usr/bin/env bash
bash -c "\$(cat "$TMP/hook-cmd")" > "$TMP/hook-out" 2>&1
echo \$? > "$TMP/hook-rc"
exit 1
HOOK
chmod +x "$DECOY/.git/hooks/pre-commit"

fingerprint() {
  # Every file under the decoy, its worktree and their git dirs: refs, objects, index,
  # config, HEAD, logs. The hook is excluded because it is the instrument.
  ( cd "$TMP" && find decoy decoy-wt -type f ! -path 'decoy/.git/hooks/*' -print0 \
      | sort -z | xargs -0 cksum ) 2>/dev/null | cksum
}

try_hook() {  # try_hook <command>  -> runs the command inside a real pre-commit
  printf '%s' "$1" > "$TMP/hook-cmd"
  rm -f "$TMP/hook-rc"
  ( cd "$WT" && git commit -q -m "a real commit in a linked worktree" ) >/dev/null 2>&1
  cat "$TMP/hook-rc" 2>/dev/null || echo "hook did not run"
}

try_hook "true" >/dev/null   # settle anything a first refused commit writes
baseline="$(fingerprint)"

tests=()
for f in "$HERE"/test-lanes.sh "$HERE"/tests-*.sh "$HERE"/tests-*.py; do
  [ -f "$f" ] || continue
  [ "$(basename "$f")" = "$SELF" ] && continue
  tests+=("$f")
done

for t in "${tests[@]}"; do
  name="$(basename "$t")"
  case "$t" in *.py) cmd="python3 '$t'" ;; *) cmd="bash '$t'" ;; esac
  echo "$name"
  bash -c "$cmd" >/dev/null 2>&1; clean_rc=$?

  GIT_DIR="$DECOY/.git" GIT_INDEX_FILE="$DECOY/.git/index" GIT_WORK_TREE="$DECOY" \
    bash -c "$cmd" >/dev/null 2>&1; env_rc=$?
  now="$(fingerprint)"
  if [ "$now" = "$baseline" ]; then ok "A. exported GIT_DIR and GIT_INDEX_FILE: the decoy is untouched"
  else bad "A. exported GIT_DIR and GIT_INDEX_FILE: the test wrote into the decoy repo"; baseline="$now"; fi
  [ "$env_rc" = "$clean_rc" ] && ok "A. ...and it exits as it does clean ($clean_rc)" \
    || bad "A. ...and it exits $env_rc, where a clean run exits $clean_rc"

  hook_rc="$(try_hook "$cmd")"
  now="$(fingerprint)"
  if [ "$now" = "$baseline" ]; then ok "B. inside a real pre-commit in a linked worktree: the decoy is untouched"
  else bad "B. inside a real pre-commit in a linked worktree: the test wrote into the decoy repo"; baseline="$now"; fi
  [ "$hook_rc" = "$clean_rc" ] && ok "B. ...and it exits as it does clean ($clean_rc)" \
    || bad "B. ...and it exits $hook_rc, where a clean run exits $clean_rc"
done

echo ""
echo "tests-fixture-isolation: $([ "$fails" -eq 0 ] && echo "PASS (${#tests[@]} tests)" || echo "FAIL ($fails)")"
exit "$([ "$fails" -eq 0 ] && echo 0 || echo 1)"
