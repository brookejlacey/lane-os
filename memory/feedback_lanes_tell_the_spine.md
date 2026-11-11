---
name: lanes-tell-the-spine
description: "A lane that stages a draft tells the spine session in the same turn; the human is never the relay"
metadata:
  type: feedback
---

**Rule.** A lane that stages a draft in `brain/drafts/` tells the spine session in the same turn, with SendMessage to that session. The human is never the relay.

**Why:** a draft nobody knows about waits for the next `/catchup`. A block message that says "open another window" makes the human carry the fact by hand.

**How to apply:** stage the draft, then message the spine session with its path and one line on what it holds. No spine session open: say so in the reply; Check 6 warns on a draft older than seven days.
