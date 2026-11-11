---
name: ask-the-far-end
description: "A script's own output is its opinion; after a write someone else reads, query the destination"
metadata:
  type: feedback
---

**Rule.** After a write that someone else reads, query the destination. A script's own output is its opinion of what it did.

**Why:** `$?` after a pipe is the pipe's status. An empty extract passes every check run on it. A deploy that exits 0 can serve the old page.

**How to apply:**
- Sent a file: read it back from where it landed.
- Wrote a row: select it.
- Pushed: compare `git rev-parse HEAD` with the remote.
