---
name: drive-a-lane-you-cannot-write
description: "A lane you cannot write is still a lane you can drive with a headless session in that repo"
metadata:
  type: feedback
---

**Rule.** A lane you cannot write is still a lane you can drive: `cd <repo> && claude -p "<goal>"`. Hand the human the window only when a session already works there.

**Why:** the write-lane guard stops the wrong write, not the work. A headless session in the right repo writes with that lane's rules.

**How to apply:** the handoff states goal, boundary and the facts it cannot discover (`memory/feedback_handoff_goals_not_steps.md`). Check its commit with `git show --stat HEAD` in that repo.
