---
name: recall
description: Answer "what do I know about X" by searching the whole spine (brain/, memory/, projects/, desks/) with ripgrep, following [[wikilinks]], and synthesizing a cited answer with a staleness note. No database and no embeddings: disciplined search plus the model doing the synthesis. Use when you say "/recall X", "what do I know about X", "what's the latest on X", or "pull everything on X".
---

# /recall

The spine's retrieval layer. The read-on-demand pointer works because the spine is
small. As `brain/` + `memory/` + `projects/` grow past what fits in a glance, you need
search, not just a pointer. This closes that gap the Lane OS way: ripgrep plus wikilinks
plus the model, with no engine, no Postgres, and no embeddings to keep warm.

Given a topic or query:

1. **Search broad.** ripgrep the query and obvious synonyms across the spine,
   case-insensitive, with a little context:
   `rg -i -C2 "<query>" brain/ memory/ projects/ desks/ global/ --type md`
   Also scan the `MEMORY.md` index and the frontmatter `description:` lines, so you find
   files whose body never says the literal term but whose summary does.

2. **Follow the links.** For every hit, pull its `[[wikilink]]` references and open those
   files too. The spine is a graph; the real answer is often one hop from the first hit.

3. **Rank.** Weight by recency (file mtime, plus any "Last updated" or dated headers) and
   by hit density. Put the freshest, most-referenced sources first.

4. **Synthesize, do not dump.** Write the ANSWER in prose, with a `file:line` citation
   after each claim so every line is verifiable. This is the whole difference between
   search (raw pages) and recall (the answer).

5. **Flag staleness.** End with a one-line heads-up when the freshest relevant source is
   old, or when a referenced `[[wikilink]]` points at a file that does not exist
   ("nothing on this since <date>", or "referenced [[x]] is missing"). Knowing what you do
   NOT have is half the value.

Read-only. `/recall` never writes; it answers. To capture something new, use `/spark`.
