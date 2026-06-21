---
name: since
description: Catch up on everything since the last real working session. File a digest into the right lane STATUS files plus a cross-cutting line in the weekly log. File-and-propose only; never auto-acts. Workspace-root (spine) sessions only.
---

# /since

Backward-looking ingest of what happened while you were away.

1. Compute the real gap since the last working session (ignore automated commits).
2. Pull in whatever happened in that window from your wired sources (meeting notes,
   email, commits).
3. Classify each item by lane, extract decisions and action items, and file a digest
   into the right `projects/<name>/STATUS.md` plus a cross-cutting line in
   `brain/WEEKLY_LOG.md`.
4. **File and propose only.** List proposed next actions for you to greenlight; never
   auto-spawn work.

Workspace-root (spine) sessions only (it writes `brain/` and `projects/`).
