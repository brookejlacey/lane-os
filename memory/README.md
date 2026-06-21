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
- After writing a file, add a one-line pointer to `MEMORY.md` under the right section.
- In the body, link related memories with `[[name]]`. A link to a not-yet-written
  memory is fine; it marks something worth writing later.
