---
name: note-first-rule-second
description: "Memory is for what a future session will rely on unchecked; a correction is a note first, an always-loaded rule only on the second miss, a hook only where the harm is outward or cannot be undone"
metadata:
  type: feedback
---

**Rule.** Memory is for what a future session will rely on without re-checking. Write when the human asks or it is clearly worth it. A correction is a note first. It becomes an always-loaded rule only when the same miss happens a second time. It gets a hook only where the harm is outward or cannot be undone.

**Why:** an earlier version of this rule said every miss becomes a rule plus a check, with a commit check that failed whenever the share of gated rules dropped. In the spine this scaffold came from, the always-loaded rules file went from 51 rules to 103 in four months under that ratchet, while longer instruction files lower how well a model follows each line. The ratchet was retired. Every hook was kept.

**How to apply:**
- **What to write.** A fact you had to be told, a stated preference, a correction, a recipe no code holds. Not what code, git or the brain files already say.
- **Where.** One rule, one file. A rule that loads in every session is one line in `global/CLAUDE.md` naming its file. A rule that applies in one place is one line where that place loads it. Everything else is one line in `memory/MEMORY.md`. Detail lives in the file, never in the loaded line. A new incident about an existing rule goes under that file's `## History`.
- **The order.** Note first. A second miss of the same kind (`/recall` shows whether there was a first) earns a loaded line. A hook only for an outward send, a secret going public, a write into the wrong lane or anything else that cannot be taken back.
- **WARN first.** A new check or hook ships as a warning. It blocks only after it has passed on real work with no false positive. The promoting commit says how many.
- **A gate may retire,** on a count of its real blocks in the session transcripts. The outward-harm gates never retire on a count.
- **Budgets.** The loaded files have ceilings in `scripts/check-file-budgets.py`, so a new line is paid for by a trimmed one.
- When the human says "make that a rule" or "gate that", `/reflect implement` builds it.

## History
- The ratchet era: a counter of gated rules, a triage file for the ungateable ones and a commit check that failed when coverage dropped. Retired with all three, no hook removed.
