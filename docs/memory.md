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

`MEMORY.md` is the index, loaded each session as a table of contents. A rule's own line
names its file wherever the rule loads (`global/CLAUDE.md`, the spine's `CLAUDE.md`, the
lane lines, a desk's `CLAUDE.md`), so the index lists only the files no rule names. The
index tells a session what exists; the session opens the specific files it needs.

## One rule, one file

A rule's loaded line is one line. Its file holds the rule in full, the why, how to apply
it and a `## History` of the misses behind it. A new incident about an existing rule goes
under that history, never into a second file beside it. Keeping the detail out of the
loaded line is what keeps the always-loaded files short.

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

## When to write one

A memory is a prediction that a future session will rely on the fact without checking it
again. Write when the human asks or when that is clearly true. A correction is a note
first. It becomes a loaded rule line only when the same miss happens a second time
([`miss-to-rule-loop.md`](miss-to-rule-loop.md)).

## How facts get in

Saving a fact used to depend on the model noticing, mid-session, that a fact was
durable. `/reflect` makes the sweep a step: it dedups against what is already recorded,
stages additive facts in `brain/drafts/` for the next spine merge, and puts anything
that would change an always-loaded instruction under a section the human decides.
`/reflect implement`, on the human's ask, makes a note a rule line or a gate. `/recall`
searches the spine and the session transcripts, so a session can check whether a miss
happened before.

`scripts/lane-doctor.sh` (Check 3) keeps the index honest: every memory file named by a
rule or listed in the index, every `[[wikilink]]` resolving. `memory/MEMORY.md` carries a byte budget like every other
file a session reads whole.
