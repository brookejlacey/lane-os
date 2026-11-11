---
name: write-only-your-lane
description: "A session writes only the lane it owns plus brain/drafts/; only the spine session writes the spine, even when asked"
metadata:
  type: feedback
---

**Rule.** A session writes only the lane it owns plus the shared inbox `brain/drafts/`. A code session writes its repo and its `projects/<name>/` mirror. A desk writes its `desks/<topic>/`. Only the spine session writes `brain/`, `memory/`, `global/` or `skills/`. This holds even when the human asks.

**Why:** parallel sessions that all write the same shared files conflict on git. Accuracy of the content does not justify the wrong lane.

**How to apply:** decline before the write. Stage the fact in `brain/drafts/` and tell the spine session (`memory/feedback_lanes_tell_the_spine.md`). The guard `scripts/hooks/block-cross-lane-write.py` blocks it anyway; Check 9 proves the guard still blocks. Full: `docs/write-lane-invariant.md`.
