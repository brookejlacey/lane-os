# AGENTS.md

This repository is a **Lane OS spine**: the shared context layer for running many
single-topic AI coding sessions in parallel without conflicts, with the rules that govern
it enforced by hooks and commit checks.

If you are an AI agent working in this repo, read these first, in order:

1. `global/CLAUDE.md`, the behavioral constitution (loaded every session in a real deployment)
2. The `SessionStart` read-directive (it tells you which lane you are in and what to read)
3. `docs/write-lane-invariant.md`, the one rule you must never break

The single most important rule: **write only to the lane you are in.** If your working
directory is a code repo (or its `projects/<name>/` mirror), you write that repo and its
mirror, never the spine's `brain/`, `memory/`, `global/` or `skills/`. If you are in a
desk, you write only that desk. Only a spine (workspace-root) session rebuilds the
cross-cutting files. When in doubt, stage to `brain/drafts/` and stop.

Before you commit here: `bash scripts/audit-cheap.sh` must PASS. The pre-commit hook
runs it on the staged set. If you add a rule bullet to `global/CLAUDE.md`, either name
its gate or add a row to `global/rule-triage.tsv`, then restate the coverage line from
`python3 scripts/find-decayed-rules.py --count`.

This is the public, generic scaffold. In a real deployment every template file is
filled with private context and the repo itself is private.
