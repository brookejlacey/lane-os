#!/usr/bin/env bash
# Asserts what the INSTALLED commit gate does, by driving real commits and merges.
#
# A gate that passes when its checker is gone looks exactly like a gate that passed a
# clean commit, so a text check of the hook template proves nothing. This installs the
# hooks into a throwaway repo with scripts/install-git-hooks.sh and asserts:
#
#   1. the installer writes pre-commit AND pre-merge-commit, with the same body
#   2. a clean commit passes, and the checker ran with --quiet --staged
#   3. a staged violation is REJECTED, from the top level and from a subdirectory
#   4. a missing checker REFUSES the commit; so does one that is not executable
#   5. AUDIT_CHEAP_SKIP=1 skips only the checker: another hook still runs and still blocks
#   6. a merge that brings in a violation is REJECTED (git skips pre-commit on a merge),
#      and a clean merge still lands
#
# It re-runs itself under env -i with a scratch HOME, so nothing from the caller's shell
# (a GIT_DIR or GIT_INDEX_FILE exported by an outer pre-commit, an AUDIT_CHEAP_SKIP left
# set, a global hooks path) can reach a git call here. Every repo lives in a temp dir.
set -uo pipefail

SELF="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)/$(basename "${BASH_SOURCE[0]}")"
if [ -z "${_TIGH_INNER:-}" ]; then
  _home="$(mktemp -d)"
  _path=/usr/bin:/bin
  for _tool in git python3; do
    _dir="$(dirname "$(command -v "$_tool" 2>/dev/null || echo /usr/bin/x)")"
    case ":$_path:" in *":$_dir:"*) ;; *) _path="$_path:$_dir" ;; esac
  done
  env -i HOME="$_home" PATH="$_path" _TIGH_INNER=1 bash "$SELF" "$@"
  rc=$?
  rm -rf "$_home"
  exit "$rc"
fi

# ---- inside the minimal environment from here on ----
SRC="$(dirname "$SELF")"   # the real scripts/ directory, read only
T="$HOME"
fails=0
ok()    { echo "  ok    $1"; }
bad()   { echo "  FAIL  $1"; fails=$((fails + 1)); }
check() { if [ "$2" = "$3" ]; then ok "$1"; else bad "$1 (expected $2, got $3)"; fi; }
has()   { if printf '%s' "$3" | grep -qF -- "$2"; then ok "$1"; else bad "$1 (output lacks: $2)"; fi; }

head_sha() { git -C "$1" rev-parse -q --verify HEAD 2>/dev/null || echo none; }
try_commit() {  # try_commit <dir> <msg> [VAR=value...]  -> OUT, RC
  local dir="$1" msg="$2"; shift 2
  OUT="$(cd "$dir" && env "$@" git commit -q -m "$msg" 2>&1)"; RC=$?
}

FX="$T/fx"
mkdir -p "$FX/scripts"
git -C "$FX" init -q
git -C "$FX" config user.email test@example.invalid
git -C "$FX" config user.name test
git -C "$FX" config commit.gpgsign false
git -C "$FX" checkout -q -b main
cp "$SRC/install-git-hooks.sh" "$FX/scripts/install-git-hooks.sh"
STUB_LOG="$T/stub.log"
# A stub checker: records its argv and fails when a STAGED file carries the marker.
cat > "$FX/scripts/audit-cheap.sh" <<STUB
#!/usr/bin/env bash
echo "\$*" >> "$STUB_LOG"
for f in \$(git diff --cached --name-only --diff-filter=ACMR); do
  if git show ":\$f" 2>/dev/null | grep -q PLANTED_VIOLATION; then echo "FAIL planted violation in \$f"; exit 1; fi
done
exit 0
STUB
chmod +x "$FX/scripts/audit-cheap.sh" "$FX/scripts/install-git-hooks.sh"
echo base > "$FX/README.md"
git -C "$FX" add README.md scripts
git -C "$FX" commit -q -m baseline   # no hooks installed yet

echo "1. install"
inst_out="$(bash "$FX/scripts/install-git-hooks.sh" 2>&1)"; inst_rc=$?
check "the installer exits 0" 0 "$inst_rc"
HOOKS="$(git -C "$FX" rev-parse --absolute-git-dir)/hooks"
[ -x "$HOOKS/pre-commit" ] && ok "pre-commit is installed and executable" || bad "pre-commit is not installed"
[ -x "$HOOKS/pre-merge-commit" ] && ok "pre-merge-commit is installed and executable" || bad "pre-merge-commit is not installed"
if [ -f "$HOOKS/pre-merge-commit" ] && cmp -s "$HOOKS/pre-commit" "$HOOKS/pre-merge-commit"; then
  ok "both hooks carry the same body"
else
  bad "pre-merge-commit differs from pre-commit, or is missing"
fi
has "the installer names both hooks" "pre-merge-commit" "$inst_out"

echo "2-3. a clean commit, then a violation"
: > "$STUB_LOG"
echo "clean work" > "$FX/clean.txt"; git -C "$FX" add clean.txt
before="$(head_sha "$FX")"
try_commit "$FX" "clean change"
check "a clean commit passes" 0 "$RC"
[ "$(head_sha "$FX")" != "$before" ] && ok "the clean commit landed" || bad "the clean commit did not land"
has "the checker ran with --quiet --staged" "--quiet --staged" "$(cat "$STUB_LOG")"

echo "PLANTED_VIOLATION here" > "$FX/bad.txt"; git -C "$FX" add bad.txt
before="$(head_sha "$FX")"
try_commit "$FX" "sneak it in"
[ "$RC" -ne 0 ] && ok "a staged violation is rejected (rc=$RC)" || bad "a staged violation was committed"
check "the rejected commit left HEAD where it was" "$before" "$(head_sha "$FX")"
mkdir -p "$FX/sub"
try_commit "$FX/sub" "from a subdirectory"
[ "$RC" -ne 0 ] && ok "rejected from a subdirectory too" || bad "a subdirectory commit let the violation through"
git -C "$FX" reset -q

echo "4. a missing or non-executable checker refuses the commit"
base4="$(head_sha "$FX")"
echo "ok" > "$FX/c2.txt"; git -C "$FX" add c2.txt
mv "$FX/scripts/audit-cheap.sh" "$T/audit-cheap.saved"
try_commit "$FX" "checker gone"
[ "$RC" -ne 0 ] && ok "a missing checker refuses the commit (rc=$RC)" || bad "a missing checker let the commit pass"
check "...and HEAD stayed where it was" "$base4" "$(head_sha "$FX")"
has "...and the refusal names the checker" "missing or not executable" "$OUT"
has "...and names the one skip that exists" "AUDIT_CHEAP_SKIP=1" "$OUT"
mv "$T/audit-cheap.saved" "$FX/scripts/audit-cheap.sh"
git -C "$FX" reset -q --hard "$base4"
echo "ok" > "$FX/c3.txt"; git -C "$FX" add c3.txt
chmod -x "$FX/scripts/audit-cheap.sh"
try_commit "$FX" "checker not executable"
[ "$RC" -ne 0 ] && ok "a non-executable checker refuses the commit (rc=$RC)" || bad "a non-executable checker let the commit pass"
check "...and HEAD stayed where it was" "$base4" "$(head_sha "$FX")"
chmod +x "$FX/scripts/audit-cheap.sh"
git -C "$FX" reset -q --hard "$base4"
echo "ok" > "$FX/c4.txt"; git -C "$FX" add c4.txt
try_commit "$FX" "checker back"
check "the restored checker passes a clean commit" 0 "$RC"

echo "5. AUDIT_CHEAP_SKIP=1 skips only the checker"
base5="$(head_sha "$FX")"
# A second, unrelated hook, the kind a fork adds: it rejects a marker in the message.
printf '#!/usr/bin/env bash\nif grep -q REJECT_THIS_MESSAGE "$1"; then echo "commit-msg: rejected"; exit 1; fi\n' > "$HOOKS/commit-msg"
chmod +x "$HOOKS/commit-msg"
echo "PLANTED_VIOLATION skipped on purpose" > "$FX/skip.txt"; git -C "$FX" add skip.txt
before="$(head_sha "$FX")"
try_commit "$FX" "REJECT_THIS_MESSAGE" AUDIT_CHEAP_SKIP=1
[ "$RC" -ne 0 ] && ok "the other hook still runs and blocks under AUDIT_CHEAP_SKIP=1" || bad "AUDIT_CHEAP_SKIP=1 disarmed another hook"
check "...and HEAD stayed where it was" "$before" "$(head_sha "$FX")"
try_commit "$FX" "skip the checker" AUDIT_CHEAP_SKIP=1
check "AUDIT_CHEAP_SKIP=1 lets the commit past the checker" 0 "$RC"
has "...and says so" "AUDIT_CHEAP_SKIP=1" "$OUT"
rm -f "$HOOKS/commit-msg"
git -C "$FX" reset -q --hard "$base5"

echo "6. a merge is checked too"
git -C "$FX" checkout -q -b feature
echo "PLANTED_VIOLATION from a branch" > "$FX/branch.txt"; git -C "$FX" add branch.txt
git -C "$FX" commit -q --no-verify -m "a branch commit the gate never saw"   # fixture setup only
git -C "$FX" checkout -q main
echo "main moved on" > "$FX/main.txt"; git -C "$FX" add main.txt
git -C "$FX" commit -q -m "main moves"
before="$(head_sha "$FX")"
OUT="$(cd "$FX" && git merge --no-ff -q -m "merge feature" feature 2>&1)"; RC=$?
[ "$RC" -ne 0 ] && ok "a merge that brings in a violation is rejected (rc=$RC)" || bad "the merge brought a violation in unchecked"
check "...and HEAD stayed where it was" "$before" "$(head_sha "$FX")"
git -C "$FX" merge --abort 2>/dev/null || git -C "$FX" reset -q --hard "$before"
git -C "$FX" checkout -q feature
git -C "$FX" rm -q branch.txt
echo "clean branch work" > "$FX/branch-ok.txt"; git -C "$FX" add branch-ok.txt
git -C "$FX" commit -q -m "the branch cleans up"
git -C "$FX" checkout -q main
: > "$STUB_LOG"
before="$(head_sha "$FX")"
OUT="$(cd "$FX" && git merge --no-ff -q -m "merge feature" feature 2>&1)"; RC=$?
check "a clean merge lands" 0 "$RC"
[ "$(head_sha "$FX")" != "$before" ] && ok "...as a merge commit" || bad "the clean merge did not land"
has "...and the checker ran on it" "--quiet --staged" "$(cat "$STUB_LOG")"

echo ""
if [ "$fails" -eq 0 ]; then echo "tests-install-git-hooks: PASS"; exit 0; fi
echo "tests-install-git-hooks: FAIL ($fails)"
exit 1
