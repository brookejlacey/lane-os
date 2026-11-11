# Spine repo

<!-- Loaded only by sessions whose cwd is inside the spine: the spine session, the desks and the project mirrors. The rules for every session are in global/CLAUDE.md (~/.claude/CLAUDE.md links to it) and are not repeated here. A code window never loads this file; its lane lines are printed by hooks/session-start.sh. The rules sync never copies this file. Each line is the rule; the memory/ file it names holds the detail. Budget: scripts/check-file-budgets.py. -->

## The spine session

- **Only the spine session writes the spine;** a desk or a mirror session inside this repo writes its own folder plus `brain/drafts/`, even when asked. Hook: `block-cross-lane-write.py`; Check 9. `memory/feedback_write_only_your_lane.md`
- **A lane you cannot write is still a lane you can drive:** `cd <repo> && claude -p "<goal>"`. `memory/feedback_drive_a_lane_you_cannot_write.md`
- **Ask the neighbouring lane before re-deriving what it already knows.** `memory/feedback_ask_the_neighbouring_lane.md`
- Code: a repo under a workspace root, state in `projects/<name>/`. Desk: `desks/<topic>/`. Map: `switchboard/SWITCHBOARD.html`.
- Routing: the write target owns the window; a raw idea goes to `/spark`, `/spin-lane` graduates it. Table: `global/REFERENCE.md`.

## Brain

- Instructions changed = restart. Content changed = `/catchup`, which also merges `brain/drafts/`.
- Brevity: ACTIVE_NOW 1-3 sentences a bullet; WEEKLY_LOG two weeks; a draft drained within seven days. Checks 5, 6.
- **Every file a session reads whole carries a byte budget,** a code repo's own instruction files included; a code repo's `CLAUDE.md` holds mechanism only. Check 4. `memory/feedback_budgets_not_brevity_rules.md`
- **Every open concern declares a Probe or an Owner** and is probed, never re-dated. Checks 7, 8. `memory/feedback_concerns_declare_their_close.md`
- `memory/` is one fact per file. A rule's line names its file; every other file is one line in `memory/MEMORY.md`. Check 3.
