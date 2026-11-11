---
name: concerns-declare-their-close
description: "Every open concern declares a Probe the machine runs or an Owner who closes it; it is probed, never re-dated"
metadata:
  type: feedback
---

**Rule.** Every open concern declares how it closes: a `**Probe:**` the machine runs, or an `**Owner:**`, the one person or lane who can close it. An open concern is probed, never re-dated.

**Why:** a concern with neither has nobody closing it. A concern re-dated each week looks fresh while it rots.

**How to apply:** `scripts/probe-concerns.py` runs the probes and stamps them; a probe flags, a human confirms. Check 8 fails a concern with neither; Check 7 warns on one older than 30 days. Full: `docs/concerns.md`.
