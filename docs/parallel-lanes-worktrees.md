# Parallel work in one lane: worktrees

The write-lane guard stops a session writing into another lane. It does not stop two
sessions in the same lane sharing one checkout, and that collision is real: a driven
session's interleaved commit landing under your session's commit message, a `git reset`
in one window silently unstaging what the other staged.

**Two sessions must never share one checkout.** A branch separates history. A worktree
separates the files, and the collision is a file problem.

```bash
git worktree add ../<name>-<task> -b <branch>   # a second, isolated checkout of the same repo
git worktree remove ../<name>-<task>            # on merge
```

- Use one when two sessions must work in one repo at the same time, when `main` must
  stay releasable during a long change, or when two states must run side by side.
- Do not use one for separate repos, or for one change after another. One window per
  repo stays the default.
- A worktree isolates files only. Both sessions still share one database, one deploy
  target, one app-store console. Bar the second session from every deploy and store
  action in its handoff.
- A new worktree has no `node_modules` and no `.env.local`, because both are gitignored.
  Each one needs its own install.

## Driven sessions share the git index

When a spine session drives a lane (`cd <repo> && claude -p "<goal>"`) to edit that
lane's `projects/<name>/` mirror, the child writes and commits into the same spine
checkout the parent is using. The working tree is shared, and so is `.git/index`, which
is a single file with no per-session isolation.

- While a driven session is running, the parent runs no `git add`, `git commit`,
  `git reset` or `git stash` in the spine. Write files freely; stage nothing.
- Drive lanes one at a time when they write into the spine.
- Tell the child in its handoff: stage and commit in one step, never a bare `git reset`.
- Verify after with `git show --stat HEAD`, and confirm the commit contains what its
  message claims. Do not trust that the commit you just made is the commit you meant.
- Large or long-running lane work gets its own worktree instead.

## Honest status

This page is judgment, not a gate: nothing mechanical stops two sessions opening the
same checkout. A per-lane lockfile that queues a headless drive behind an open window
would make it one, and is the obvious next gate to build. `global/rule-triage.tsv`
records it as judgment for that reason, with the reason.
