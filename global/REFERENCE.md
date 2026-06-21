# Reference (read on demand)

Lookup material that does NOT need to be in context every session. `global/CLAUDE.md`
carries the behavioral rules and points here. Read this when doing machine setup,
debugging the SessionStart hook, onboarding a new repo or machine, or changing how
config syncs.

## Session routing (which session to open for what)

**Mental shorthand:** if you are writing code, open the code repo. If you are writing
about the work at large, open the spine.

| Working on... | Open a session in... |
|---|---|
| Code (any product repo) | That repo |
| Project-specific docs, status updates | That repo's session (writes land in `projects/<name>/`) or the spine |
| Cross-cutting context (ACTIVE_NOW, DECISIONS, CONCERNS, PEOPLE) | The spine (workspace-root) |
| An ongoing non-code topic | Its `desks/<topic>/` |
| Daily orient, cross-project planning, merges | The spine |

**The mid-session switch:** if something cross-cutting surfaces while you are in a
code lane, do NOT update the spine from there. Drop a note in the lane's `STATUS.md`
or stage to `brain/drafts/`, and let a spine session merge it. Editing spine files
from a code lane is exactly what the write-lane guard blocks.

## Session lifecycle: restart vs refresh

Sessions load `CLAUDE.md`, the SessionStart hook output, and skill files once into
context at start. Mid-session edits to those do NOT auto-refresh. Other files
(`brain/`, `STATUS.md`, code) are read on demand and stay fresh.

Mnemonic: **instructions changed = restart. Content changed = refresh** (re-pull +
re-read, e.g. via a `/catchup` skill).

| What changed | What to do |
|---|---|
| `global/CLAUDE.md`, a skill file, the hook script, settings | Restart the affected session(s) |
| `brain/*.md`, a `STATUS.md`, memory bodies, code | Refresh (`/catchup`) in the affected session(s) |

## SessionStart hook contract

Hook script: `hooks/session-start.sh`. On every session it:

1. Locates the spine repo (auto-detects common locations, or honors `LANE_OS_ROOT`).
2. Pulls the spine repo fast-forward-only (never auto-merges from a hook).
3. Refreshes the user-level `~/.claude/CLAUDE.md` from `global/CLAUDE.md` (skipped if
   it is already a symlink).
4. Symlinks repo skills into `~/.claude/skills/` and prunes links to deleted skills.
5. Pulls the current code repo too if the session is inside one.
6. Emits a compact **read-directive** naming the exact files this lane should read.

**Why a directive and not the file contents:** hook stdout is truncated to a small
inline preview when large; anything past that is written to a file the model does not
auto-read. So the hook must NOT print full brain/status files. It prints a short,
always-delivered pointer telling the session to Read those files itself, which
delivers the full content reliably via the Read tool.

The directive is lane-aware: a code lane is told to read its `STATUS.md` + the brain
priorities; a desk is told to read its own `CLAUDE.md` + `LOG.md`; a spine session
is told to read the cross-cutting priorities.

## Symlink architecture

The spine repo is the single source of truth. Symlinks make sure edits land in it
with no drift:

- `~/.claude/CLAUDE.md` -> `<spine>/global/CLAUDE.md`
- `~/.claude/skills/<name>` -> `<spine>/skills/<name>` (one per skill; the hook keeps
  these current automatically)
- `~/.claude/hooks/session-start.sh` -> `<spine>/hooks/session-start.sh`

Keep these as symlinks, never copies: a copy goes stale silently and is the classic
cause of "the hook is not picking up my change."

## Multi-machine sync

`git pull` the spine repo. Brain files, statuses, global config, and skills all come
with it. Code syncs through each repo. No dual-write once symlinks are in place.

If a push is rejected, `git pull --rebase` and retry. On a merge conflict, surface it
rather than resolving blind.

## Onboarding a new lane

- **New code lane:** create `projects/<repo-name>/` in the spine (copy
  `projects/_TEMPLATE/`). The hook keys context injection on the repo's folder name,
  so the names must match.
- **New desk:** copy `desks/_TEMPLATE/` to `desks/<topic>/` and fill its `CLAUDE.md`.
- `scripts/new-lane.sh` does either for you.
