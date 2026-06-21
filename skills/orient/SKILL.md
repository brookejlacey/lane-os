---
name: orient
description: The single sit-down command. Refreshes context, surfaces anything to file, and hands you the plan at the right horizon. Run from a spine (workspace-root) session. Trigger when you sit down to work, say "orient me", "I'm back", or "where do I start".
---

# /orient

The front door for sitting down to work. Composes the other lifecycle skills so you
remember one entry point instead of four.

1. **Refresh** (`/catchup`): pull the spine + current repo, re-read `brain/ACTIVE_NOW.md`
   and `brain/CONCERNS.md` so this session knows the current state.
2. **File** (optional `/since`): if time has passed, surface anything that needs to be
   logged before planning. Propose, never auto-file.
3. **Plan**: hand back the plan at the right horizon. Default to the daily slice
   (`/today`); use the weekly arc (`/week`) if the argument asks for it or it has been
   a while.

Workspace-root (spine) sessions only. Optional argument `today` or `week` forces the
horizon.
