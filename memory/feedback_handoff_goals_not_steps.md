---
name: handoff-goals-not-steps
description: "A handoff to another session states GOAL, BOUNDARY and the facts it cannot discover, never steps"
metadata:
  type: feedback
---

**Rule.** A handoff states GOAL, BOUNDARY and the facts the other session cannot discover. Never implementation steps.

**Why:** the receiving session can read its own repo. Steps written from outside it are guesses that it then follows into a wall.
