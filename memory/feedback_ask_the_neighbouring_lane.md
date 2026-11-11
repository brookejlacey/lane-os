---
name: ask-the-neighbouring-lane
description: "Ask the lane that already knows before re-deriving its work; each lane's focus is in the switchboard"
metadata:
  type: feedback
---

**Rule.** Ask the neighbouring lane before re-deriving what it already knows. `switchboard/state.json` carries each lane's `focus`. Overlap means message that session, never a write into its lane.

**Why:** two sessions working out the same fact from scratch spend twice and can disagree.
