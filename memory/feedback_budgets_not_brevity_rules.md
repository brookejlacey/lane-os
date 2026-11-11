---
name: budgets-not-brevity-rules
description: "Every file a session reads whole carries a byte budget in one table; a prose brevity rule alone lets it grow"
metadata:
  type: feedback
---

**Rule.** Every file a session reads whole carries a byte budget in one table, `scripts/check-file-budgets.py`. Prune before you add. Move history to an archive file verbatim.

**Why:** measured over four months in the spine this came from, the two always-loaded files with a byte ceiling stayed flat while the two governed only by a written brevity rule grew 2x and 5.2x.

**How to apply:** Check 4 runs the table on every commit. Full: `docs/context-budgets.md`.
