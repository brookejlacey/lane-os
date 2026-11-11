---
name: one-checkout-per-session
description: "Two sessions never share one checkout; same lane at the same time means a worktree"
metadata:
  type: feedback
---

**Rule.** Two sessions never share one checkout. Same lane at the same time: `git worktree add ../<name>-<task> -b <branch>`.

**Why:** a branch separates history but a worktree separates the files, which is what collides. Two sessions in one checkout share one git index, so one session's `git add` lands in the other's commit.

**How to apply:** `docs/parallel-lanes-worktrees.md`. Nothing mechanical blocks this yet; it holds only while read.
