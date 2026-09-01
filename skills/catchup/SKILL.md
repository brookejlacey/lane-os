---
name: catchup
description: Refresh this session's understanding without restarting. Pull the spine + current repo, re-read brain/ACTIVE_NOW.md and brain/CONCERNS.md, and report what changed. In a spine session it also merges brain/drafts, probes the open concerns, syncs the rules if the constitution changed, and runs the drift checks. Use when another session may have pushed updates this session does not know about.
---

# /catchup

Content changed, not instructions. Use this to re-sync a running session.

## Every lane

1. `git pull --ff-only` the spine, and the current code repo if you are in one. If a pull
   fails, say why (behind/ahead, or offline); do not resolve a conflict blind.
2. Re-read `brain/ACTIVE_NOW.md` and `brain/CONCERNS.md`, plus this lane's `STATUS.md`
   and `MEMORY.md` (code lane) or `CLAUDE.md` and `LOG.md` (desk).
3. Skim `switchboard/state.json` for lanes whose `focus` overlaps what you are about to
   do. Overlap means message that session, never a write into its lane.
4. Report what changed in 3-5 bullets.

## Spine session only (workspace-root)

5. **Merge `brain/drafts/`.** For each staged file, route its content into the right
   brain file, memory file or lane mirror, then delete the draft. A `## NEEDS A HUMAN`
   section is surfaced, never applied. `brain/drafts/ideas/` is `/spark`'s inbox and is
   left for `/spin-lane`.
6. **Probe the concerns.** `python3 scripts/probe-concerns.py`. Confirm each READY TO
   CLOSE item against its evidence, then move it to `brain/archive/` with that evidence.
   Put DECISIONS OWED in front of the human once. Give every new concern a Probe or an
   Owner.
7. **Rebuild the brain coherently**: `ACTIVE_NOW` from `projects/*/STATUS.md` (1-3
   sentences per bullet, depth stays in STATUS), `WEEKLY_LOG` trimmed to two weeks,
   `CONCERNS` pruned, never re-dated.
8. **If `global/CLAUDE.md` changed**, `python3 scripts/sync-rules.py`. A row reading
   `deferred: session open` is not a failure.
9. `bash scripts/audit-cheap.sh` must PASS, then commit and push.

Instructions changed (a skill, the constitution, the hook)? That is a restart, not a
catchup.
