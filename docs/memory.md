# The memory system

Lane OS keeps two kinds of persistent knowledge, and it is worth being clear on the
difference.

- **`brain/`** is STATE: what is true right now, changing constantly, rebuilt by spine
  sessions. Short, and read near the top of most sessions.
- **`memory/`** is FACTS: durable things that do not change often, one per file, pulled
  in by relevance rather than read wholesale.

## One fact per file

Each memory is a small markdown file with frontmatter:

```markdown
---
name: <short-kebab-case-slug>
description: <one-line summary, used to decide relevance during recall>
metadata:
  type: user | feedback | project | reference
---

<the fact>
```

`MEMORY.md` is the index: one line per memory, loaded each session as a table of
contents. The index tells a session what exists; the session opens the specific files
it needs.

## The four types

- **user** - who the human is: role, expertise, preferences.
- **feedback** - how the agent should work, with the why. Capture corrections here so
  the same correction is never needed twice.
- **project** - ongoing work or constraints not derivable from code or git history.
- **reference** - pointers to external resources.

## Discipline that keeps memory useful

- Update an existing file rather than creating a near-duplicate.
- Delete memories that turn out to be wrong.
- Do not store what the repo already records (structure, past fixes, history).
- Link related memories with `[[name]]` so recall pulls the cluster, not just the hit.
- A recalled memory reflects what was true when written; verify a named file or flag
  still exists before acting on it.

## How facts get in

Saving a fact used to depend on the model noticing, mid-session, that a fact was
durable. `/reflect` makes the sweep a step: it dedups against what is already recorded,
stages additive facts in `brain/drafts/` for the next spine merge, and puts anything
that would change an always-loaded instruction under a section the human decides.
`/reflect implement` goes one step further and lands a learning as a gate. See
[`miss-to-rule-loop.md`](miss-to-rule-loop.md).

`scripts/lane-doctor.sh` (Check 3) keeps the index honest: every memory file listed,
every `[[wikilink]]` resolving. `memory/MEMORY.md` carries a byte budget like every other
file a session reads whole.
