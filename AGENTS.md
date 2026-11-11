# AGENTS.md

This repository is a **Lane OS spine**: the shared context layer for running many
single-topic AI coding sessions in parallel without conflicts, with the rules that govern
it enforced by hooks and commit checks.

If you are an AI agent working in this repo, read these first, in order:

1. `global/CLAUDE.md`, the rules for every session (loaded every session in a real deployment)
2. `CLAUDE.md` at the root, the rules for sessions inside the spine
3. The `SessionStart` read-directive (it tells you which lane you are in, prints the lane
   rules and names what to read)
4. `docs/write-lane-invariant.md`, the one rule you must never break

The single most important rule: **write only to the lane you are in.** If your working
directory is a code repo (or its `projects/<name>/` mirror), you write that repo and its
mirror, never the spine's `brain/`, `memory/`, `global/` or `skills/`. If you are in a
desk, you write only that desk. Only a spine (workspace-root) session rebuilds the
cross-cutting files. When in doubt, stage to `brain/drafts/` and stop.

Before you commit here: `bash scripts/audit-cheap.sh` must PASS. The pre-commit hook
runs it on the staged set. A new rule is one line where it applies (`global/CLAUDE.md` for
every session, the root `CLAUDE.md` for sessions inside the spine, the lane lines in
`hooks/session-start.sh` for lanes) naming the memory file that holds its detail and the
gate when there is one. Check 1 fails a line that names a file that does not exist.

This is the public, generic scaffold. In a real deployment every template file is
filled with private context and the repo itself is private.
