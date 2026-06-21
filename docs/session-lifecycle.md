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
2. Pulls the spine fast-forward-only.
3. Refreshes `~/.claude/CLAUDE.md` from the constitution (unless it is a symlink).
4. Symlinks skills into `~/.claude/skills/` and prunes dead links.
5. Pulls the current code repo if the session is in one.
6. Emits a compact, lane-aware **read-directive**.

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

## Refreshing a long-running or remote session

If you drive a session over remote control and cannot restart it easily, a
`/catchup`-style skill re-pulls and re-reads content. Note that it does not reload the
constitution or skills, which bind at process start; for those, a real restart is the
only guarantee.
