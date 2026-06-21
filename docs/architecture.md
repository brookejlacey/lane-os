# Architecture: three lane types, one spine

## The spine

One git repository is the spine. It holds everything cross-cutting:

- `global/` - the constitution (`CLAUDE.md`) and read-on-demand `REFERENCE.md`.
- `brain/` - the context layer: identity, current priorities, decisions, concerns,
  people, a rolling log. These are short state files, rebuilt by spine sessions.
- `memory/` - durable facts, one per file, indexed by `MEMORY.md`.
- `skills/` - reusable slash-commands.
- `projects/` - a thin STATUS + MEMORY mirror for each code lane.
- `desks/` - one folder per topic desk.

The spine is private in a real deployment. This public repo is the generic template.

## Code lanes

A code lane is one of your actual code repositories, anywhere on disk. The spine holds
only a thin mirror at `projects/<repo-name>/` (a `STATUS.md` and a `MEMORY.md`). The
repo's folder name and the mirror folder name must match, because the SessionStart
hook keys context injection on the name.

A code-lane session writes its own repo and its own mirror. That is the carve-out that
lets a code session record its state without reaching into the spine's brain files.

## Topic desks

A desk is an ongoing non-code subject: finances, planning, research, a reading queue,
anything you return to repeatedly that is not a codebase. Each desk is
`desks/<topic>/` with its own `CLAUDE.md` (its contract and posture) and `LOG.md` (its
running record). A desk session reads its own `CLAUDE.md` first and works from its
slice; it does not load the whole brain.

## Why mirror code lanes instead of putting status in the repo

Two reasons. First, it keeps all of your cross-project state in one place (the spine),
so a spine session can synthesize across everything without cloning every repo.
Second, it keeps private working notes out of code repos that might be public or
shared. The code lives in the repo; the running commentary lives in the mirror.

## How a session knows which lane it is in

The SessionStart hook looks at the working directory:

- Inside a git repo that is not the spine -> **code lane** (named by the repo folder).
- Inside `spine/desks/<topic>/` -> **desk**.
- Inside the spine but not under `desks/` -> **spine (workspace-root)**.

It then injects a directive naming that lane's write boundary and the exact files to
read. See `docs/session-lifecycle.md`.
