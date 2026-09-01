#!/usr/bin/env bash
# audit-cheap.sh: the fast, mechanical drift detector for a Lane OS spine.
#
# Catches in about a second what a human would only notice by re-reading: broken file
# references in instruction docs, a memory index out of sync, a state file over its byte
# budget, a stale WEEKLY_LOG window, drafts rotting in staging, concerns that never
# declared how they close, a write-lane guard that has quietly stopped blocking, a hook
# that exists but is registered nowhere, a coverage claim that no longer matches the
# rules file, a shared repo that would receive the private rules, a reply-length pair
# that disagrees with itself, and a credential in a staged file.
#
# NOT a semantic audit. This catches the cheap stuff so the LLM pass only has to do the
# hard stuff. Every check names its number; the constitution names the check on the
# rule it enforces, which is what makes "gated" a measurable word.
#
# Usage:
#   scripts/audit-cheap.sh              # full working-tree view
#   scripts/audit-cheap.sh --staged     # judge only what this commit contains (pre-commit)
#   scripts/audit-cheap.sh --quiet      # only FAIL lines
#   scripts/audit-cheap.sh --strict     # exit 1 on WARN as well as FAIL
#   scripts/audit-cheap.sh --repo PATH  # run against another checkout (spine-only checks skip)
#
# Exit: 0 clean (or WARN without --strict), 1 a FAIL, 2 usage error.
# Wire it: bash scripts/install-git-hooks.sh   (pre-commit runs --quiet --staged)

set -uo pipefail

REPO_PATH=""; QUIET=0; STRICT=0; STAGED=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo) REPO_PATH="$2"; shift 2 ;;
    --quiet) QUIET=1; shift ;;
    --strict) STRICT=1; shift ;;
    --staged) STAGED=1; shift ;;
    -h|--help) sed -n '2,/^$/p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

SELF_REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." 2>/dev/null && pwd -P)"
[[ -z "$REPO_PATH" ]] && REPO_PATH="$SELF_REPO"
if ! git -C "$REPO_PATH" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "audit-cheap: not a git repo: $REPO_PATH" >&2; exit 2
fi
cd "$REPO_PATH"
REPO_PATH="$(pwd -P)"

IS_SPINE=0
[[ -f "global/CLAUDE.md" && -d "brain" && -d "memory" ]] && IS_SPINE=1

# Is THIS spine the one installed on this machine? Registration checks only make sense
# then; a second checkout (a fork you are reviewing) must not be judged against another
# spine's settings.json.
INSTALLED_HERE=0
if [[ -L "$HOME/.claude/CLAUDE.md" ]]; then
  _target="$(cd "$(dirname "$(readlink "$HOME/.claude/CLAUDE.md")")" 2>/dev/null && pwd -P)"
  [[ "$_target" == "$REPO_PATH/global" ]] && INSTALLED_HERE=1
fi

FAIL_COUNT=0; WARN_COUNT=0; INFO_COUNT=0
fail() { echo "FAIL · $*"; FAIL_COUNT=$((FAIL_COUNT + 1)); }
warn() { [[ "$QUIET" -eq 0 ]] && echo "WARN · $*"; WARN_COUNT=$((WARN_COUNT + 1)); }
info() { [[ "$QUIET" -eq 0 ]] && echo "INFO · $*"; INFO_COUNT=$((INFO_COUNT + 1)); }
section() { [[ "$QUIET" -eq 0 ]] && echo "" && echo "── $* ──"; }
TODAY="$(date +%Y-%m-%d)"

# Which files count as "changed". Parallel lane sessions share one checkout, so a commit
# gate must judge WHAT IS BEING COMMITTED: --staged narrows every changed-file scan to
# the index. An unstaged edit is not skipped, only deferred to the commit that stages it.
# Interactive runs keep the wide working-tree view.
changed_paths() {
  if git rev-parse --verify HEAD >/dev/null 2>&1; then
    if [[ "$STAGED" -eq 1 ]]; then
      git diff --cached --name-only --diff-filter=ACMR HEAD -- "$@" 2>/dev/null
    else
      git diff --name-only --diff-filter=ACMR HEAD -- "$@" 2>/dev/null
      git ls-files --others --exclude-standard -- "$@" 2>/dev/null
    fi
  else
    git diff --cached --name-only --diff-filter=ACMR -- "$@" 2>/dev/null
    [[ "$STAGED" -eq 1 ]] || git ls-files --others --exclude-standard -- "$@" 2>/dev/null
  fi
}

# ── Check 1: broken file references in instruction docs ────────────────────
# A path in backticks that no longer exists is an instruction the agent will follow into
# a wall. Scans the files an agent reads as instructions, skips placeholders (<name>, *).
section "Check 1: broken file references"
if [[ "$IS_SPINE" -eq 1 ]]; then
  _docs=$(ls global/*.md AGENTS.md README.md docs/*.md skills/*/SKILL.md 2>/dev/null)
  _broken=$(grep -ohE '`(scripts|hooks|global|brain|memory|skills|docs|projects|desks|switchboard)/[A-Za-z0-9_./*<>-]+`' $_docs 2>/dev/null \
    | tr -d '`' | grep -vE '[<>*]' | sort -u \
    | while IFS= read -r p; do [[ -e "$p" || -e "${p%/}" ]] || echo "$p"; done)
  if [[ -n "$_broken" ]]; then
    fail "instruction docs reference paths that do not exist:"
    printf '%s\n' "$_broken" | sed 's/^/      /'
  else
    info "every backticked repo path in the instruction docs exists"
  fi
fi

# ── Check 2: skill symlink sanity ──────────────────────────────────────────
# A skill copied instead of linked goes stale silently. Only judged on the machine
# where this spine is the installed one.
section "Check 2: skill symlink sanity"
if [[ "$IS_SPINE" -eq 1 && "$INSTALLED_HERE" -eq 1 ]]; then
  _bad=""
  for d in skills/*/; do
    n="$(basename "$d")"; l="$HOME/.claude/skills/$n"
    if [[ ! -L "$l" ]]; then _bad="$_bad $n"; fi
  done
  if [[ -n "$_bad" ]]; then warn "skills not symlinked into ~/.claude/skills:$_bad (the SessionStart hook links them; restart a session)"
  else info "every skill is a symlink in ~/.claude/skills"; fi
elif [[ "$IS_SPINE" -eq 1 ]]; then
  info "skipped: this checkout is not the spine installed on this machine"
fi

# ── Check 3: memory index and wikilinks (lane-doctor) ──────────────────────
section "Check 3: memory index shape and wikilinks"
if [[ "$IS_SPINE" -eq 1 && -x scripts/lane-doctor.sh ]]; then
  if _ld=$(bash scripts/lane-doctor.sh 2>&1); then
    info "lane-doctor: every wikilink resolves and every memory fact is indexed"
    printf '%s\n' "$_ld" | grep -E '^\s+WARN' | while IFS= read -r l; do warn "${l#"${l%%[![:space:]]*}"}"; done
  else
    fail "lane-doctor found dangling wikilinks or an unindexed memory:"
    printf '%s\n' "$_ld" | grep -E 'FAIL|WARN' | sed 's/^/      /'
  fi
fi

# ── Check 4: state-file byte budgets ───────────────────────────────────────
# One table, scripts/check-file-budgets.py. Exit 2 = hard ceiling, 1 = warn.
section "Check 4: state-file byte budgets"
if [[ "$IS_SPINE" -eq 1 && -f scripts/check-file-budgets.py ]]; then
  _b=$(python3 scripts/check-file-budgets.py --over-only 2>&1); _rc=$?
  if [[ "$_rc" -eq 2 ]]; then fail "a state file is over its HARD ceiling; every lane pays this before it is asked anything:"; printf '%s\n' "$_b"
  elif [[ "$_rc" -eq 1 ]]; then warn "a state file is over budget; move history to an archive file verbatim, do not delete it:"; printf '%s\n' "$_b"
  else info "every tracked state file is inside its byte budget"; fi
fi

# ── Check 5: WEEKLY_LOG rolling 2-week window ──────────────────────────────
section "Check 5: WEEKLY_LOG rolling window"
if [[ -f brain/WEEKLY_LOG.md ]]; then
  _old=$(python3 - brain/WEEKLY_LOG.md "$TODAY" <<'PY'
import re, sys
from datetime import datetime
today = datetime.strptime(sys.argv[2], "%Y-%m-%d")
for wk in re.findall(r"^## Week of (\d{4}-\d{2}-\d{2})", open(sys.argv[1]).read(), re.M):
    age = (today - datetime.strptime(wk, "%Y-%m-%d")).days
    if age > 14:
        print(f"'Week of {wk}' is {age}d old (>14d window): move it to an archive file")
PY
)
  if [[ -n "$_old" ]]; then printf '%s\n' "$_old" | while IFS= read -r l; do warn "$l"; done
  else info "WEEKLY_LOG holds only the last two weeks"; fi
fi

# ── Check 6: brain/drafts staleness ────────────────────────────────────────
# A draft is a rule or fact in staging. Unmerged, it rots: sessions re-learn what it
# already says. Older than 7 days means run /catchup.
section "Check 6: brain/drafts staleness"
if [[ "$IS_SPINE" -eq 1 && -d brain/drafts ]]; then
  _stale=$(find brain/drafts -type f -name '*.md' ! -name 'README.md' -mtime +7 2>/dev/null | sort)
  if [[ -n "$_stale" ]]; then
    warn "brain/drafts has $(printf '%s\n' "$_stale" | grep -c .) draft(s) older than 7 days; run /catchup to drain:"
    printf '%s\n' "$_stale" | head -10 | sed 's/^/      /'
  else info "no draft has sat in brain/drafts for more than 7 days"; fi
fi

# ── Check 7: open concerns are dated within 30 days ────────────────────────
# An open concern is probed, never re-dated. Older than 30 days (or undated) means the
# next spine session probes its live source and closes, updates, or surfaces it.
section "Check 7: open concerns dated within 30 days"
if [[ -f brain/CONCERNS.md ]]; then
  _stale=$(python3 - <<'PY'
import datetime, re
today = datetime.date.today()
text = open("brain/CONCERNS.md", encoding="utf-8").read()
m = re.search(r"^## Right Now\b.*$", text, re.M)
if m:
    body = text[m.end():]
    nxt = re.search(r"^## ", body, re.M)
    if nxt: body = body[:nxt.start()]
    for raw in re.findall(r"^### .*(?:\n(?!### |## ).*)*", body, re.M):
        flat = " ".join(raw.split())
        if "[Example" in flat or "PARKED" in flat:
            continue
        dates = [datetime.date.fromisoformat(d) for d in re.findall(r"20\d\d-\d\d-\d\d", flat)]
        label = re.sub(r"^[-*#\s]*", "", flat)[:72]
        if not dates: print(f"UNDATED · {label}")
        elif (today - max(dates)).days > 30: print(f"{(today - max(dates)).days}d old · {label}")
PY
)
  if [[ -n "$_stale" ]]; then
    warn "open concern(s) stale or undated; probe the live source, then close, update or surface each:"
    printf '%s\n' "$_stale" | sed 's/^/      /'
  else info "all open concerns are dated within 30 days"; fi
fi

# ── Check 8: every open concern declares a Probe or an Owner ───────────────
section "Check 8: open concerns declare a Probe or an Owner"
if [[ -f brain/CONCERNS.md && -f scripts/probe-concerns.py ]]; then
  if _pc=$(python3 scripts/probe-concerns.py --check 2>&1); then info "$_pc"
  else fail "$(printf '%s' "$_pc" | head -1)"; printf '%s\n' "$_pc" | tail -n +2 | sed 's/^/      /'; fi
fi

# ── Check 9: the write-lane guard actually blocks ──────────────────────────
# A fail-open guard cannot report its own death: a broken guard and an approving guard
# look identical from outside. So assert its behavior on every commit, both directions.
section "Check 9: write-lane guard is live"
if [[ "$IS_SPINE" -eq 1 && -f scripts/test-lanes.sh ]]; then
  if _tl=$(bash scripts/test-lanes.sh 2>&1); then
    info "write-lane guard: $(printf '%s' "$_tl" | tail -1)"
  else
    fail "the write-lane guard is not enforcing the invariant (scripts/test-lanes.sh):"
    printf '%s\n' "$_tl" | grep FAIL | sed 's/^/      /'
  fi
fi

# ── Check 10: every blocking hook is registered ────────────────────────────
# A hook file that exists but is wired into no settings file is invisible: it looks
# exactly like a rule nobody tripped. Existence is not enforcement.
section "Check 10: blocking hooks are registered"
if [[ "$IS_SPINE" -eq 1 && "$INSTALLED_HERE" -eq 1 ]]; then
  _settings="$HOME/.claude/settings.json"; _missing=""
  for _hk in scripts/hooks/block-*.py scripts/hooks/preflight-reply-length.py scripts/hooks/advisory-reply-length.py; do
    [[ -f "$_hk" ]] || continue
    grep -q "$(basename "$_hk")" "$_settings" 2>/dev/null || _missing="$_missing $(basename "$_hk")"
  done
  if [[ -n "$_missing" ]]; then fail "hook(s) exist but are registered nowhere in $_settings:$_missing (run scripts/install.sh)"
  else info "every guard and the reply-length pair are registered in ~/.claude/settings.json"; fi
elif [[ "$IS_SPINE" -eq 1 ]]; then
  info "skipped: this checkout is not the spine installed on this machine"
fi

# ── Check 11: the commit gate scopes to the staged set ─────────────────────
# The gate reads a file set, so the set it reads IS the gate. Widening it back to the
# whole tree would re-break every parallel lane session and nothing green would show it.
section "Check 11: commit gate scopes to the staged set"
_gate_test="scripts/tests-audit-cheap-staged.sh"
if [[ "$IS_SPINE" -eq 1 && -z "${AUDIT_CHEAP_SELFTEST:-}" ]]; then
  if [[ ! -f "$_gate_test" ]]; then fail "$_gate_test is missing; --staged scoping has no test"
  else
    _changed=$(changed_paths scripts/audit-cheap.sh "$_gate_test" scripts/install-git-hooks.sh)
    if [[ -z "$_changed" ]]; then info "scoping test skipped (the gate's own code did not change)"
    elif _out=$(AUDIT_CHEAP_SELFTEST=1 bash "$_gate_test" 2>&1); then info "commit gate scopes to the staged set, and still blocks what is staged"
    else fail "commit-gate scoping test failed:"; printf '%s\n' "$_out" | sed 's/^/      /'; fi
  fi
  # .git/hooks is not tracked, so a pull never updates the installed hook. Repair it.
  _hook="$(git rev-parse --git-path hooks/pre-commit 2>/dev/null)"
  if [[ "$REPO_PATH" == "$SELF_REPO" && -f "$_hook" ]] && ! grep -q -- '--staged' "$_hook"; then
    if bash scripts/install-git-hooks.sh >/dev/null 2>&1; then info "installed pre-commit hook was stale (whole-tree scope); reinstalled with --staged"
    else fail "installed pre-commit hook scans the whole working tree; run: bash scripts/install-git-hooks.sh"; fi
  fi
fi

# ── Check 12: the gated-rule coverage ratchet ──────────────────────────────
# global/CLAUDE.md opens by stating how many of its bullets are machine-enforced. That
# number is measured from the file, never hand-typed, and restating it downward means
# naming which gate was removed and why.
section "Check 12: gated-rule coverage ratchet"
if [[ -f global/CLAUDE.md && -f scripts/find-decayed-rules.py ]]; then
  read -r _g _j _u <<< "$(python3 scripts/find-decayed-rules.py --count 2>/dev/null)"
  _t=$(( ${_g:-0} + ${_j:-0} + ${_u:-0} ))
  _claim=$(grep -oE 'Coverage today: [0-9]+ of [0-9]+' global/CLAUDE.md | head -1)
  _cg=$(printf '%s' "$_claim" | awk '{print $3}'); _ct=$(printf '%s' "$_claim" | awk '{print $5}')
  if [[ -z "$_claim" ]]; then fail "global/CLAUDE.md no longer states 'Coverage today: N of M bullets are gated'; that line is the ratchet's baseline"
  elif [[ "$_g" != "$_cg" || "$_t" != "$_ct" ]]; then fail "global/CLAUDE.md claims '$_claim' but measures $_g of $_t; restate it from scripts/find-decayed-rules.py --count"
  else info "gated-rule coverage: $_g of $_t bullets name a Hook or a Check ($(( _g * 100 / (_t > 0 ? _t : 1) ))%), $_j triaged as judgment"; fi
  if [[ "${_u:-0}" -gt 0 ]]; then warn "$_u rule(s) are neither gated nor triaged (the decay surface): scripts/find-decayed-rules.py --untriaged"; fi
fi

# ── Check 13: shared repos never receive the rules ─────────────────────────
# The deny list for the rules sync derives from the publisher's own audience table, so
# a repo created for an outside reader is denied the day it exists. Assert the link.
section "Check 13: shared repos never receive the global rules"
if [[ "$IS_SPINE" -eq 1 && -f scripts/tests-shared-repos-never-sync.py ]]; then
  if _sr=$(python3 scripts/tests-shared-repos-never-sync.py 2>&1); then info "$(printf '%s' "$_sr" | tail -1)"
  else fail "the rules sync could reach a shared repo:"; printf '%s\n' "$_sr" | grep -E 'FAIL' | sed 's/^/      /'; fi
fi

# ── Check 14: the reply-length pair agrees with itself ─────────────────────
# Two halves of one rule that disagree about when the rule applies are worse than
# either half alone. Assert the shared constants match and both self-tests pass.
section "Check 14: reply-length pair agrees"
_a=scripts/hooks/advisory-reply-length.py; _p=scripts/hooks/preflight-reply-length.py
if [[ -f "$_a" && -f "$_p" ]]; then
  _same=$(python3 - "$_a" "$_p" <<'PY'
import re, sys
def consts(path):
    src = open(path, encoding="utf-8").read()
    limit = re.search(r"^WORD_LIMIT\s*=\s*(\d+)", src, re.M)
    ask = re.search(r"^DETAIL_ASK\s*=\s*re\.compile\((.*?)\)\n", src, re.M | re.S)
    return (limit.group(1) if limit else None, ask.group(1).strip() if ask else None)
print("same" if consts(sys.argv[1]) == consts(sys.argv[2]) else "differ")
PY
)
  if [[ "$_same" != "same" ]]; then fail "advisory-reply-length.py and preflight-reply-length.py disagree on WORD_LIMIT or DETAIL_ASK"
  elif ! python3 "$_a" --self-test >/dev/null 2>&1; then fail "advisory-reply-length.py self-test fails"
  elif ! python3 "$_p" --self-test >/dev/null 2>&1; then fail "preflight-reply-length.py self-test fails"
  else info "reply-length pair shares its limit and carve-outs; both self-tests pass"; fi
fi

# ── Check 15: no credential in a changed file ──────────────────────────────
# Runs in any repo, not just the spine. Patterns require a real key length so a doc
# that mentions the prefix does not trip it. This script is excluded from its own scan.
section "Check 15: no credential in a changed file"
_secret_re='((^|[^A-Za-z0-9-])sk-[A-Za-z0-9_-]{20,}|ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|AKIA[0-9A-Z]{16}|xox[baprs]-[A-Za-z0-9-]{20,}|-----BEGIN [A-Z ]*PRIVATE KEY-----)'
_hits=""
while IFS= read -r f; do
  [[ -n "$f" && -f "$f" ]] || continue
  [[ "$f" == "scripts/audit-cheap.sh" ]] && continue
  if [[ "$STAGED" -eq 1 ]]; then _content=$(git show ":$f" 2>/dev/null); else _content=$(cat "$f" 2>/dev/null); fi
  _m=$(printf '%s' "$_content" | grep -nE "$_secret_re" 2>/dev/null | head -3 | cut -c1-80)
  [[ -n "$_m" ]] && _hits="$_hits
      $f: $_m"
done < <(changed_paths)
if [[ -n "$_hits" ]]; then fail "a changed file carries something shaped like a credential:$_hits"
else info "no credential shape in the changed files"; fi

# ── Result ─────────────────────────────────────────────────────────────────
section "Result"
echo "FAIL: $FAIL_COUNT · WARN: $WARN_COUNT · INFO: $INFO_COUNT"
if [[ "$FAIL_COUNT" -gt 0 ]]; then echo "audit-cheap: FAIL"; exit 1; fi
if [[ "$STRICT" -eq 1 && "$WARN_COUNT" -gt 0 ]]; then echo "audit-cheap: WARN (strict)"; exit 1; fi
echo "audit-cheap: PASS"; exit 0
