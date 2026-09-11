# Architecture: three lane types, one spine

## The spine

One git repository is the spine. It holds everything cross-cutting:

- `global/`: the constitution (`CLAUDE.md`), the judgment triage (`rule-triage.tsv`),
  and the read-on-demand `REFERENCE.md`.
- `brain/`: the synthesis layer: identity, current priorities, decisions, concerns,
  people, a rolling log. Short state files, rebuilt by spine sessions from the lanes'
  mirrors and the drafts every lane may stage.
- `memory/`: durable facts, one per file, indexed by `MEMORY.md`.
- `skills/`: reusable slash-commands.
- `projects/`: a thin `STATUS.md` + `MEMORY.md` mirror for each code lane.
- `desks/`: one folder per topic desk.
- `scripts/` and `hooks/`: the mechanisms that enforce all of the above.
- `switchboard/`: a local, gitignored map of what every lane is doing.

The spine is private in a real deployment. This public repo is the generic template.

## Code lanes

A code lane is one of your actual code repositories, anywhere under a workspace root.
The spine holds only a thin mirror at `projects/<repo-name>/`: a `STATUS.md` (session
state, goes stale by design) and a `MEMORY.md` (durable facts about the lane, outranks
STATUS when they disagree). The repo folder and the mirror folder share a name, because
the hook and the guard key on it.

A code-lane session writes its own repo and its own mirror. Opening a terminal in the
mirror (`projects/<name>/`) is the same lane, addressed from the spine side; it does not
become a spine session by being inside the spine.

The lane's own `CLAUDE.md` holds mechanism only (commands, gotchas, hard rules) and
imports the synced constitution. Release state lives in the mirror, not the repo.

## Topic desks

A desk is an ongoing non-code subject: finances, research, a reading queue, anything
you return to repeatedly that is not a codebase. Each desk is `desks/<topic>/` with its
own `CLAUDE.md` (its contract and posture) and `LOG.md` (its running record). A desk
session reads its own `CLAUDE.md` first and works from its slice; it does not load the
whole brain.

A **voice register** is a desk with two more files and a corpus: one register of one
person's writing, so a session in it cannot answer in another register's voice or edit
another register's files. Scaffold it with `scripts/new-lane.sh voice <register>`. See
`docs/voice-layer.md`.

## Why mirror code lanes instead of putting status in the repo

Two reasons. First, it keeps all of your cross-project state in one place, so a spine
session can synthesize across everything without cloning every repo, and the switchboard
can read what each lane is on. Second, it keeps private working notes out of code repos
that might be public or shared. The code lives in the repo; the running commentary lives
in the mirror.

## How a session knows which lane it is in

The SessionStart hook looks at the working directory:

- Inside a git repo that is not the spine: **code lane** (named by the repo folder).
- Inside `spine/projects/<name>/`: the same **code lane**, from the mirror.
- Inside `spine/desks/<topic>/`: **desk**.
- Inside the spine otherwise: **spine (workspace-root)**.

It then injects a directive naming that lane's write boundary and the exact files to
read. See `docs/session-lifecycle.md`. The guard makes the same classification from the
same rule, and `scripts/test-lanes.sh` asserts the two agree on 25 representative writes.

## The read side: the switchboard

Lanes never write each other. They do read each other, through `switchboard/`: a
per-machine map built by `scripts/build-switchboard.py` with each lane's last human
commit and its current `focus` (the newest dated heading in its STATUS or LOG). A session
that finds overlap with a neighbour's focus messages that lane, or drives it, instead of
re-deriving its work. See `docs/switchboard.md`.
