# Session lifecycle: the hook, restart vs refresh

## What loads when

A session loads three things once, at start: the constitution (`CLAUDE.md`), the
SessionStart hook output, and any skill files it uses. These are cached for the life
of the session. Everything else (`brain/` files, a lane's `STATUS.md`, the code) is
read on demand and stays fresh.

This split drives the core mnemonic:

**Instructions changed = restart. Content changed = refresh (`/catchup`).**

If you edit the constitution, a skill, or the hook script, restart the sessions that
need the new behavior. If you edit brain or status content, a `/catchup` re-pulls and
re-reads it without losing your session history.

## The SessionStart hook

`hooks/session-start.sh` runs on every session start. It:

1. Locates the spine repo (via `LANE_OS_ROOT` or auto-detection).
2. Pulls the spine fast-forward-only, and records why if that fails (behind/ahead, or offline).
3. Refreshes `~/.claude/CLAUDE.md` from the constitution (unless it is a symlink).
4. Symlinks skills into `~/.claude/skills/` and prunes dead links.
5. Pulls the current code repo if the session is in one.
6. Detects the lane: code repo, code lane from its `projects/<name>/` mirror, desk, or spine.
7. Emits a compact, lane-aware **read-directive**, plus a trailer: an ACTION line when
   `brain/drafts/` holds staged files, any pull failure, and a SWITCHBOARD pointer with
   the lane count and build time.
8. Refreshes the switchboard in the background.

## Why a directive, not the file contents

Hook stdout gets truncated to a small inline preview when it is large; anything past
that is written to a file the model does not automatically read. If the hook printed
your full brain and status files, only the first couple of kilobytes would reach the
session, and the session would silently operate on a fraction of its context. That is
the single most common way a context system fails: it looks like it delivered the
content, but it did not.

So the hook stays small. It prints a short, always-delivered pointer that names the
exact files to read, and instructs the session to Read them itself. The Read tool then
delivers the full content reliably. The directive is phrased as blocking ("Read these
before your first reply") because the observed failure mode is a session answering
from the index alone instead of opening the files.

The same reasoning is why the files it points at carry byte budgets
([`context-budgets.md`](context-budgets.md)): a pointer to a 30k file is a 30k cost paid
by every session before it is asked anything.

## The other hooks in a session

| Event | Hook | Does |
|---|---|---|
| PreToolUse | `scripts/hooks/block-cross-lane-write.py` | Blocks an out-of-lane write |
| UserPromptSubmit | `scripts/hooks/preflight-reply-length.py` | One line of context before the reply, only when recent replies drifted long |
| Stop | `scripts/hooks/advisory-reply-length.py` | Measures the reply into a local log; silent |

`scripts/install.sh` registers all of them. See [`reply-length-gate.md`](reply-length-gate.md).

## What a spine session does at sit-down

`/orient` (or `/catchup`): pull, re-read `ACTIVE_NOW` and `CONCERNS`, merge
`brain/drafts/` into the right files, run `scripts/probe-concerns.py` so open concerns are
probed rather than re-dated, and, if the constitution changed, `scripts/sync-rules.py`.
`bash scripts/audit-cheap.sh` before the commit catches what that pass missed.

## Refreshing a long-running or remote session

If you drive a session over remote control and cannot restart it easily, `/catchup`
re-pulls and re-reads content. It does not reload the constitution or skills, which bind
at process start; for those, a real restart is the only guarantee.
