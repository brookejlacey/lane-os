# The write-lane invariant

This is the one rule that makes everything else work. It is structural, not a
preference: break it and parallel sessions corrupt each other's state.

## The rule

**A session may write only to the lane it owns, plus the shared `brain/drafts/` inbox.**

| Session lane | May write | May NOT write |
|---|---|---|
| Code lane (cwd is the repo, or `projects/<name>/`) | its own repo, `projects/<name>/`, `brain/drafts/` | the rest of the spine, other repos, other mirrors |
| Desk | its own `desks/<topic>/`, `brain/drafts/` | the rest of the spine, other desks, repos |
| Spine (workspace-root) | the whole spine, `~/.claude` | another repo's code |

Scratch under `/tmp` is nobody's lane and is always allowed.

## Why it has to be a hard rule

You run sessions in parallel. If every session can write the cross-cutting files
(`brain/ACTIVE_NOW.md`, memory, the constitution), then two sessions editing them at
once conflict on git. Worse, a session editing those files in isolation has only a
partial view, so it updates one file and forgets the three related ones that should
move together. Cross-file coherence is exactly what a single spine session protects.

So the accuracy of the content does not justify the wrong lane. A code-lane session
might know a true, important fact about your week, but if it writes that into
`brain/`, it has broken the invariant. The right move is to **stage it in
`brain/drafts/`** and let a spine session merge it coherently later.

## How it is enforced

1. **The SessionStart directive** tells every session its lane and its boundary, in
   plain language, before it does anything.
2. **The PreToolUse guard** (`scripts/hooks/block-cross-lane-write.py`) resolves every
   write target against the session's lane and hard-blocks out-of-lane writes (exit 2).
   Wrong-lane work becomes impossible, not just discouraged.
3. **The test that proves the guard blocks** (`scripts/test-lanes.sh`) runs on every
   commit as `audit-cheap` Check 9.

The third is not optional. The guard fails open: if it cannot confidently identify a
violation, it allows the write, because a false block stops real work. That means a
broken guard and an approving guard are byte-identical from outside. In the spine this
came from, the guard approved every write for weeks behind a bare `except` before a
staged draft's claim about a specific hole was probed and the probe showed the guard
also failed its own docstring's example. So the test feeds it 25 representative writes,
in both directions (over-blocking is its own outage), and the commit gate runs it.

The guard also cannot see writes made through Bash redirection, so the routing reflex
(open the window that owns the work) still matters.

## The mirror is the lane

Opening a terminal in `projects/<name>/` means "I am working that lane", not "I own the
spine". Before the guard classified it that way, cd-ing one level deeper into the spine
silently bought write access to `memory/`, `global/`, `skills/` and `brain/`. Both the
hook and the guard now treat that cwd as the code lane: it may write the mirror, the
repo of the same name under a workspace root, and `brain/drafts/`.

## When asked to write out of lane

Decline and redirect BEFORE the write, never comply then apologize. Two redirects:

- "Open a spine session and ask again there," or
- "I will stage this in `brain/drafts/` for the next merge."

And a third option that is not a write at all: **a lane you cannot write is still a lane
you can drive.** `cd <repo> && claude -p "<goal>"` runs a session in the right lane from
where you are. Hand the human the window only when a session already works there.

## Same lane, two sessions

The guard stops cross-lane writes. It does not stop two sessions in the same lane
sharing one checkout, and that collision is real. See
[`parallel-lanes-worktrees.md`](parallel-lanes-worktrees.md).

## The escape hatch

Set `LANE_GUARD_OFF=1` to disable the guard for a session where you are deliberately
doing cross-lane setup (for example, bootstrapping a brand new repo). Use it knowingly.

## Verifying the guard

```bash
bash scripts/test-lanes.sh
```

It pins `LANE_OS_ROOT` and `LANE_OS_WORKSPACE_ROOTS` to deterministic locations, stands
up throwaway git repos to play code lanes (the guard resolves a code lane with real
`git rev-parse`), and checks the exit code for each case: the drafts inbox from every
lane, the spine's own files and agent config, a code lane's repo, mirror, relative path
and scratch, the mirror-as-cwd cases, a desk's own files, and every cross-lane write
that must be refused. Exit 1 on any failure.
