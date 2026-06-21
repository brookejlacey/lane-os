---
name: spin-lane
description: Turn a captured idea into a real lane (a code repo or a topic desk), scaffolded and registered. Workspace-root (spine) sessions only. Use when you say "spin up <idea>", "make <idea> a real project", or want to graduate a /spark idea.
---

# /spin-lane

Graduate an idea from `brain/drafts/ideas/` into a working lane.

1. Read the idea file. Dedup against existing lanes (`projects/`, `desks/`).
2. For commodity work, scout prior art first (adopt before you build).
3. Stand up the right lane type:
   - **Code lane:** create the repo, then `scripts/new-lane.sh code <name>` for the
     spine mirror.
   - **Desk:** `scripts/new-lane.sh desk <name>`, then fill its `CLAUDE.md`.
4. Remove the idea file once the lane exists.

Workspace-root (spine) sessions only: it scaffolds repos and touches `projects/` and
`desks/`.
