---
name: catchup
description: Refresh this session's understanding without restarting. Pull the spine + current repo, re-read brain/ACTIVE_NOW.md and brain/CONCERNS.md, and report what changed. Use when another session may have pushed updates this session does not know about.
---

# /catchup

Content changed, not instructions. Use this to re-sync a running session.

1. `git pull` the spine repo and the current code repo (if in one).
2. Re-read `brain/ACTIVE_NOW.md` and `brain/CONCERNS.md`, plus this lane's `STATUS.md`.
3. Report a concise summary of what changed since this session last looked.

Mnemonic: **instructions changed = restart; content changed = /catchup.** This does
NOT reload `CLAUDE.md` or skills (those bind at process start); for those, restart.
