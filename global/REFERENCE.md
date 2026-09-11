# Reference (read on demand)

Lookup material that does NOT need to be in context every session. `global/CLAUDE.md`
carries the behavioral rules and points here. Read this when doing machine setup,
debugging a hook, onboarding a new repo or machine, or changing how config syncs.

## Session routing (which session to open for what)

**Mental shorthand:** if you are writing code, open the code repo. If you are writing
about the work at large, open the spine.

| Working on... | Open a session in... |
|---|---|
| Code (any product repo) | That repo |
| Project-specific docs, status updates | That repo (writes land in `projects/<name>/`), or `projects/<name>/` itself |
| Cross-cutting context (ACTIVE_NOW, DECISIONS, CONCERNS, PEOPLE) | The spine (workspace-root) |
| An ongoing non-code topic | Its `desks/<topic>/` |
| Daily orient, cross-project planning, merges | The spine |

**The mid-session switch:** if something cross-cutting surfaces while you are in a
code lane, do NOT update the spine from there. Stage to `brain/drafts/` and let a spine
session merge it. Editing spine files from a code lane is exactly what the guard blocks.
A lane you cannot write is still a lane you can drive: `cd <repo> && claude -p "<goal>"`.

## Session lifecycle: restart vs refresh

Sessions load `CLAUDE.md`, the SessionStart hook output, and skill files once at start.
Mid-session edits to those do NOT auto-refresh. Other files (`brain/`, `STATUS.md`,
code) are read on demand and stay fresh.

| What changed | What to do |
|---|---|
| `global/CLAUDE.md`, a skill file, the hook script, settings | Restart the affected session(s) |
| `brain/*.md`, a `STATUS.md`, memory bodies, code | Refresh (`/catchup`) in the affected session(s) |

## Hooks

Registered by `scripts/install.sh` in `~/.claude/settings.json`. Check 10 asserts they
stay registered.

| Event | Script | Does |
|---|---|---|
| SessionStart | `hooks/session-start.sh` | Locates the spine, pulls, links skills, detects the lane, emits the read-directive, refreshes the switchboard |
| PreToolUse (Write, Edit, MultiEdit, NotebookEdit) | `scripts/hooks/block-cross-lane-write.py` | The write-lane guard. Exit 2 blocks. Fails open on uncertainty; `LANE_GUARD_OFF=1` disables |
| Stop | `scripts/hooks/advisory-reply-length.py` | Measures the reply into `outputs/reply-length.jsonl`. Silent |
| UserPromptSubmit | `scripts/hooks/preflight-reply-length.py` | Instructs before the next reply once the log shows drift |
| git pre-commit (spine) | installed by `scripts/install-git-hooks.sh` | `audit-cheap.sh --quiet --staged` |
| git pre-commit (a shared repo) | `scripts/hooks/shared-repo-pre-commit.sh` | Refuses any staged file outside the published manifest |

## The SessionStart directive

The hook looks at the working directory:

- Inside a git repo that is not the spine: **code lane**, named by the repo folder.
- Inside `spine/projects/<name>/`: the same **code lane**, addressed by its mirror. Being
  inside the spine does not make it a spine session.
- Inside `spine/desks/<topic>/`: **desk**.
- Anywhere else in the spine: **spine (workspace-root)**.

It then prints the lane's write boundary and the exact files to read, plus a trailer:
an ACTION line when `brain/drafts/` holds staged files, a NOTE when a pull failed and
why (behind/ahead), and a SWITCHBOARD pointer. Pointers only: hook stdout truncates to a
small inline preview, and a dumped file is a silently half-read file.

## Checks (`scripts/audit-cheap.sh`)

| # | Asserts | Backing script |
|---|---|---|
| 1 | Backticked repo paths in instruction docs exist | |
| 2 | Skills are symlinks in `~/.claude/skills` | |
| 3 | Wikilinks resolve, memory is indexed | `scripts/lane-doctor.sh` |
| 4 | State files inside their byte budgets | `scripts/check-file-budgets.py` |
| 5 | `WEEKLY_LOG.md` is a 2-week window | |
| 6 | No draft older than 7 days | |
| 7 | Open concerns dated within 30 days | |
| 8 | Open concerns declare a Probe or an Owner | `scripts/probe-concerns.py --check` |
| 9 | The write-lane guard blocks | `scripts/test-lanes.sh` |
| 10 | Every guard hook is registered | |
| 11 | The commit gate judges only the staged set | `scripts/tests-audit-cheap-staged.sh` |
| 12 | The coverage line matches the file | `scripts/find-decayed-rules.py --count` |
| 13 | Shared repos never receive the rules | `scripts/tests-shared-repos-never-sync.py` |
| 14 | The reply-length pair agrees | both hooks' `--self-test` |
| 15 | No credential shape in a changed file | |
| 16 | Every voice check still fires | `scripts/check-voice.py --self-test` |
| 17 | Changed drafts carry no tell; a changed corpus was re-measured (WARN) | `scripts/check-voice.py` |

## Scripts

| Script | Purpose |
|---|---|
| `scripts/install.sh` | One-time machine setup, idempotent |
| `scripts/install-git-hooks.sh` | The pre-commit gate in the spine |
| `scripts/new-lane.sh code\|desk\|voice <name>` | Scaffold a lane |
| `scripts/lane-doctor.sh` | Dangling wikilinks, unindexed memory |
| `scripts/audit-cheap.sh` | The 17 drift checks |
| `scripts/find-decayed-rules.py` | Gated / judgment / untriaged |
| `scripts/check-voice.py` | The 13 voice checks; `--measure` reads a register's corpus |
| `scripts/probe-concerns.py` | Run every concern's Probe |
| `scripts/check-file-budgets.py` | The budget table |
| `scripts/sync-rules.py` | Constitution into every code lane |
| `scripts/publish-shared-repo.py <audience>` | A lane's cleared slice into a shared repo |
| `scripts/build-switchboard.py` | The cross-lane map |
| `scripts/build-llms-full.sh` | Regenerate `llms-full.txt` from README + docs |
| `scripts/test-lanes.sh`, `scripts/tests-*.py`, `scripts/tests-*.sh`, `--self-test` flags | Every gate proves it blocks |

## Environment variables

| Variable | Meaning |
|---|---|
| `LANE_OS_ROOT` | The spine repo. Auto-detected from common locations when unset |
| `LANE_OS_WORKSPACE_ROOTS` | Colon-separated dirs holding code repos (default `~/repos:~/work`); overrides `workspace.toml` |
| `LANE_OS_LONG_FORM_DESKS` | Comma-separated desks where a long reply is correct |
| `LANE_OS_HUMAN` | The Owner name that means "a decision only the human can make" (default `you`) |
| `LANE_GUARD_OFF=1` | Disable the write-lane guard for one session |
| `REPLY_LENGTH_ADVISORY=1` | Make the Stop half of the reply-length pair print its findings |
| `LANE_OS_SHARED_TARGET` | Override the publisher's target checkout |

## Symlink architecture

The spine repo is the single source of truth. Symlinks make sure edits land in it with
no drift: `~/.claude/CLAUDE.md` -> `<spine>/global/CLAUDE.md`, `~/.claude/skills/<name>`
-> `<spine>/skills/<name>`, `~/.claude/hooks/session-start.sh` ->
`<spine>/hooks/session-start.sh`. Keep them as symlinks, never copies.

## Onboarding a new lane

- **New code lane:** `scripts/new-lane.sh code <repo-name>`, and add a `[[repos]]` entry
  to `workspace.toml` so the rules sync reaches it. The mirror folder and the repo
  folder must share a name.
- **New desk:** `scripts/new-lane.sh desk <topic>` and fill its `CLAUDE.md`.
- **New voice register:** `scripts/new-lane.sh voice <register>`, fill its `VOICE.md`,
  pull raw samples into its `corpus/`, then
  `python3 scripts/check-voice.py --measure desks/<register> --write`. It is a desk, so
  it inherits the desk write lane.
- **New shared repo:** add an audience to `AUDIENCES` in `scripts/publish-shared-repo.py`.
  The sync denies it from that moment; Check 13 proves it.
