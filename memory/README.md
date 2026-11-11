# Memory: durable facts, one file per fact

This is a file-based long-term memory. Each fact is its own small markdown file with
frontmatter, and `MEMORY.md` is the index loaded every session.

## Frontmatter schema

```markdown
---
name: <short-kebab-case-slug>
description: <one-line summary, used to decide relevance during recall>
metadata:
  type: user | feedback | project | reference
---

<the fact. For feedback/project, follow with **Why:** and **How to apply:** lines.
Link related memories with [[their-name]].>
```

## The four types

- **user** - who the human is (role, expertise, preferences).
- **feedback** - guidance on how the agent should work, with the why.
- **project** - ongoing work or constraints not derivable from the code or git history.
- **reference** - pointers to external resources (URLs, dashboards, tickets).

## Conventions

- Before saving, check for an existing file that already covers it; update rather than
  duplicate. Delete memories that turn out wrong.
- Do not save what the repo already records (code structure, past fixes, git history).
- **One rule, one file.** A rule's detail, exceptions and history live in its file; the
  line that loads it is one line naming the file. A rule that applies in every session is
  that line in `global/CLAUDE.md`; a rule that applies in one place is that line where the
  place loads it (the spine's `CLAUDE.md`, the lane lines in `hooks/session-start.sh`, a
  desk's `CLAUDE.md`, a skill). Every other file gets a one-line pointer in `MEMORY.md`.
  Check 3 accepts either.
- **A correction is a note first.** It becomes a loaded rule line only when the same miss
  happens a second time. It gets a hook only where the harm is outward or cannot be
  undone. `feedback_note_first_rule_second.md`.
- A new incident about an existing rule goes under that file's `## History`, never into
  a second file beside it.
- In the body, link related memories with `[[name]]`. A link to a not-yet-written
  memory is fine; it marks something worth writing later.
