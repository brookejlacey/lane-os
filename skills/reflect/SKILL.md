---
name: reflect
description: Sweep a session for durable, memory-worthy items so learnings do not depend on noticing them in the moment. Three modes. Live (/reflect) stages a draft. Headless (/reflect <transcript> HEADLESS) does the same from a transcript with no human watching. Implement (/reflect implement, also "make that a rule", "gate that") lands a learning as a loaded rule line or a real gate, on the human's ask. Trigger on /reflect, "what did we learn", "make that a rule", "gate that".
---

# /reflect

Saving a fact to memory used to depend on the model noticing, mid-session, that a fact
was durable. That misses things. This skill makes the sweep a step that runs on its own.

It does **not** invent memories. Most sessions surface nothing durable and it writes
nothing. It fires on the real signal: a fact you had to be told, a preference stated
plainly, a correction, a new person or decision, a rule that should change.

## Three modes

- **Live** (`/reflect`): reflect on this conversation. Stage to `brain/drafts/`.
- **Headless** (`/reflect <transcript.jsonl> HEADLESS`): the same, from a transcript, with
  no questions asked. End with a one-line digest or `nothing durable`.
- **Implement** (`/reflect implement`, `make that a rule`, `gate that`): do everything the
  live mode does, then **land** it as a gate. Interactive only: it edits always-loaded
  instructions, which is the human's call and never a nightly job's.

All three run in-lane: staging to `brain/drafts/` is allowed from every lane. Only the
implement mode, run from a spine session, edits `global/`, `memory/` or `scripts/`.

## What counts as durable

1. A fact you had to ask for or discover that will matter again: a path, an endpoint,
   a machine detail, how a system actually behaves, where a credential lives (never
   the value).
2. A preference the human stated plainly ("always X", "never Y").
3. A correction: you did something and were corrected, or a memory is now wrong.
4. A new person or decision with its reasoning.
5. A loaded rule line (wherever it loads) or a skill that this session proved wrong or stale.

Skip anything already in `memory/`, the constitution or the brain files (dedup first);
one-off build detail (that is git history and `STATUS.md`); and anything the repo already
records.

## Tiers

- **Secret**: write the value to a secrets file outside git, put only a pointer in the
  draft. Never a value in a committed file.
- **Additive fact**: stage under `## AUTO-MERGE` in the draft, in the exact shape
  `/catchup` routes (`memory/<name>.md` new or update, `brain/PEOPLE.md`,
  `brain/DECISIONS.md`, `brain/CONCERNS.md` with its Probe or Owner).
- **Rule change, instruction removal, inferred preference**: stage under
  `## NEEDS A HUMAN`. `/catchup` surfaces this section and never applies it.

## Steps

1. Dedup: grep `memory/`, `global/CLAUDE.md`, the spine's `CLAUDE.md` and the relevant brain file for each
   candidate. Sharpen an existing entry over writing a near-duplicate.
2. **"Stop telling me X" narrows the line that produces X, before any new note.** When the
   correction is that sessions keep saying X, grep the loaded files (`global/CLAUDE.md`,
   the spine's `CLAUDE.md`, `memory/MEMORY.md`, the brain files, the skill in use) for the
   line that makes a session say X. Narrow that line first: name who it is for and where it
   never goes. A second note beside the line that causes X is a patch on a leak.
3. Sort survivors into the tiers.
4. Nothing survived (the common case): write no draft, say `nothing durable`, stop.
5. Otherwise write ONE draft at `brain/drafts/session-learning-<YYYY-MM-DD>-<slug>.md`:

```markdown
---
merge_target: session-learning
date: <YYYY-MM-DD>
---
# Session learnings

## AUTO-MERGE (catchup applies these)
- **reference -> memory/<name>.md (new):** <the fact> [[related]]
- **feedback -> memory/feedback_<name>.md (new):** <preference>. **Why:** ... **How to apply:** ...
- **concern -> brain/CONCERNS.md:** <the open unknown>. **Probe:** `<command>` or **Owner:** <who>

## NEEDS A HUMAN (catchup surfaces, does NOT apply)
- **rule change -> global/CLAUDE.md:** <what this session suggests changing, and the evidence>
```

6. Digest in 2-4 lines: what was saved or staged.

## Implement mode: from a note to a rule and from a rule to a gate

This mode runs on the human's ask ("make that a rule", "gate that"). Without the ask, the
order in `memory/feedback_note_first_rule_second.md` holds: a correction is a note first,
it becomes a loaded rule line only when the same miss happens a second time; it gets a
hook only where the harm is outward or cannot be undone. `/recall` shows whether the
miss happened before.

Per learning, two questions:

> **Where does this rule apply?** Every session: one line in `global/CLAUDE.md`. Only
> sessions inside the spine: the spine's `CLAUDE.md`. Only lanes: the lane lines in
> `hooks/session-start.sh`. One register: that desk's `CLAUDE.md`. One workflow: its skill.
> The line names its memory file; the detail lives there.

> **Does it have a deterministic signature?** An exact string, a byte count, a file that
> must or must not exist, a path pattern, a markup shape, a process that is or is not
> running.

**Yes and the harm is real: build the gate.** A hook (`scripts/hooks/block-*.py`,
PreToolUse, fails the call) when the wrong thing should never reach disk. A check (a
`section` in `scripts/audit-cheap.sh`, fails the commit) when the wrong thing is visible in
a diff.

**No: it stays a judgment rule.** Its memory file is the whole record. Say in the report
why no detector can exist. Be honest both ways: a claimed signature that does not exist
produces a check that fires on the wrong things and gets disabled, which is worse than no
check.

Four rules for the gate itself:

- Ship it as a warning. It blocks only after it has passed on real work with no false
  positive. The promoting commit says how many.
- Scope it to changed files for anything prose-shaped. A corpus-wide retrofit is a
  different decision.
- Tune it down until it is precise. A check that fires on a third of the corpus gets
  switched off, not obeyed.
- A check that cannot run must say so, never report clean having measured nothing.

**Prove it blocks.** Not that it runs. Plant the violation, watch PASS turn to FAIL,
remove it, watch PASS return. A fail-open guard cannot report its own death
(`docs/gated-rules.md`).

Then land the rest:

1. The memory file, with the scar attached: what actually went wrong, in the human's
   words where they said it. A rule without its scar reads like an opinion and the next
   session deletes it as overhead.
2. One line in the rule's home naming that file and the gate when there is one
   (`Check N`, `Hook: <name>`). The loaded files have ceilings in
   `scripts/check-file-budgets.py`, so a new line is paid for by a trimmed one.
3. `bash scripts/audit-cheap.sh` must PASS, then commit and push. Confirm
   `git rev-parse HEAD` matches `origin/main`. An edit to `global/CLAUDE.md` starts the
   rules sync on its own (`scripts/hooks/sync-rules-on-edit.sh`).

**Report** what became mechanical, not what was learned: one line per gate (the miss,
the gate, the proof it blocks), then each line that moved or narrowed, then anything left
as judgment with why no detector can exist.
