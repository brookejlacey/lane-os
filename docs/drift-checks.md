# Drift checks: audit-cheap and the commit gate

`scripts/audit-cheap.sh` is the fast, mechanical drift detector. It runs in about a
second, and it catches what a human would only notice by re-reading. It is not a
semantic audit; it catches the cheap stuff so the LLM pass only has to do the hard stuff.

```bash
bash scripts/audit-cheap.sh            # full working-tree view
bash scripts/audit-cheap.sh --staged   # judge only what this commit contains
bash scripts/audit-cheap.sh --quiet    # FAIL lines only
bash scripts/audit-cheap.sh --strict   # WARN fails too
```

Exit 0 clean, 1 a FAIL, 2 usage. Every check has a number, and the constitution names
the number on the rule it enforces; that is what makes "gated" a measurable word.

## The checks

| # | What it asserts | Level |
|---|---|---|
| 1 | Every backticked repo path in the instruction docs exists | FAIL |
| 2 | Every skill is a symlink in `~/.claude/skills` (installed spine only) | WARN |
| 3 | Every `[[wikilink]]` resolves and every memory file is indexed (`lane-doctor`) | FAIL |
| 4 | Every state file is inside its byte budget (`check-file-budgets.py`) | WARN, FAIL at a hard ceiling |
| 5 | `WEEKLY_LOG.md` holds only the last two weeks | WARN |
| 6 | No `brain/drafts/` file is older than 7 days | WARN |
| 7 | Every open concern is dated within 30 days | WARN |
| 8 | Every open concern declares a Probe or an Owner (`probe-concerns.py --check`) | FAIL |
| 9 | The write-lane guard still blocks (`test-lanes.sh`, 25 cases) | FAIL |
| 10 | Every `block-*.py` hook and the reply-length pair are registered in settings.json (installed spine only) | FAIL |
| 11 | The commit gate judges only the staged set (`tests-audit-cheap-staged.sh`, when the gate's own code changed); repairs a stale installed hook | FAIL |
| 12 | The `Coverage today: N of M` line matches `find-decayed-rules.py --count` | FAIL; WARN on untriaged rules |
| 13 | The rules sync's deny list still derives from the publisher (`tests-shared-repos-never-sync.py`) | FAIL |
| 14 | The two reply-length hooks share their limit and carve-outs, and both self-tests pass | FAIL |
| 15 | No changed file carries a credential shape (runs in any repo) | FAIL |
| 16 | Every voice check still fires on its positive sample and stays silent on its negative (`check-voice.py --self-test`) | FAIL |
| 17 | Changed drafts under a register's `outbox/` carry no tell, and a changed corpus has been re-measured | WARN |

## The commit gate

```bash
bash scripts/install-git-hooks.sh
```

installs a pre-commit hook in the spine that runs `audit-cheap.sh --quiet --staged`. A
FAIL blocks the commit. `.git/hooks/` is not tracked, so run it on every fresh clone;
Check 11 repairs a stale installed hook on its own.

`--staged` is the important word. Parallel lane sessions run against one checkout.
Without it the gate read the whole working tree, so another session's half-written file
failed this session's commit, and that session bypassed the gate with `--no-verify` over
a defect it did not write. A commit gate judges what is being committed. An unstaged edit
is not skipped, only deferred to the commit that stages it. Interactive runs keep the wide
view.

`scripts/tests-audit-cheap-staged.sh` asserts both directions in a scratch repo: a
foreign unstaged defect is ignored under `--staged`, and the same file staged still
fails. It clears the inherited git environment first, because a test that runs from a
pre-commit hook otherwise stages into the real index.

## Writing a new check

- Give it a number and a `section`. Use `fail`, `warn`, `info`.
- Scope it to `changed_paths` for anything prose-shaped. A corpus-wide retrofit is a
  different decision and usually the wrong one.
- Ship it as a WARN. It becomes a FAIL only after it has passed on real work with no
  false positive, and the promoting commit says how many. A gate that cries wolf teaches
  the next session to bypass every gate, including the ones that were right.
- Tune it until it is precise. A check that fires on a third of the corpus gets switched
  off, not obeyed.
- A check that cannot run must say so, never report clean having measured nothing.
- Say in the code what it deliberately does not catch.
- Print the count on a passing run. Slow drift is invisible to a check that only speaks
  on failure.
- Name it on the rule bullet in `global/CLAUDE.md` and restate the coverage line.
