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
