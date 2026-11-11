# From a miss to a note, a rule and sometimes a gate

A found miss gets its instance fixed. What else it gets depends on whether it has
happened before. An apology is never one of the things it gets.

1. **First time: a note.** Fix the instance. If a file was wrong, fix the file. If the
   correction is worth relying on later, write it as a memory file with the scar attached:
   what actually went wrong, in the human's words where they said it.
2. **Second time: a rule.** The same miss again earns one loaded line, in the home where
   the rule applies, naming that memory file. `/recall` shows whether there was a first
   time.
3. **A gate only where it earns its place:** the harm is outward or cannot be undone, or
   the miss has a deterministic signature that has actually recurred. It ships as a
   warning and blocks only after it has passed on real work with no false positive.

"Sorry, I'll be more careful" is a non-fix, because nothing in the system changed. A fixed
file is a fix. So is a narrowed line.

## Where the rule's line goes

A rule loads where it applies, not everywhere:

| The rule applies to | Its line goes in |
|---|---|
| Every session on every lane | `global/CLAUDE.md` |
| Sessions inside the spine (the spine session, desks, mirrors) | the spine's own `CLAUDE.md` |
| Lanes only | the lane lines `hooks/session-start.sh` prints |
| One voice register | that desk's `CLAUDE.md` |
| One workflow | its skill (`/preflight`, `/ship`) |

The line is one line. The detail lives in the memory file it names. In the spine this
came from, moving thirty rules to where they apply and the detail into the files took the
always-loaded rules from 103 lines to 72.

## "Stop telling me X" narrows a line

When the correction is that sessions keep saying X, a new note beside the cause is a patch
on a leak. Find the loaded line that makes a session say X and narrow it first: who it is
for and where it never goes.

## Fix the class when a gate is earned

When a gate is earned, build it for the whole category, not the instance. A guard that
silently approved everything became Check 9 (assert it blocks, every commit). A hook that
existed but was registered nowhere became Check 10. A draft that rotted for days became
Check 6. Each of those guards a failure that recurred, or a guard that died without anyone
seeing it.

## A caught output defect adds the missing assertion

If the human finds a property wrong after every existing check passed, encode that
property in the verifier. A green check proves only the shape it encodes. When a property
is wrong while its check is green, find the shape the check cannot see and add that
assertion instead of tightening an unrelated threshold.

## Revision-survival is a real reason for a check

Across one session that rewrote a single artifact four times, every rule with a check
held; every rule living only in prose decayed, because each rewrite re-derives the
artifact from the newest instruction and drops constraints set two rewrites earlier. So a
constraint restated across multiple drafts of one artifact needs a check, whatever else it
looks like. Code lanes get this for free from compilers and tests. Prose lanes need it
built.

## How `/reflect implement` runs it

`skills/reflect/SKILL.md`, implement mode, on the human's ask ("make that a rule", "gate
that"). Per learning it asks where the rule applies and whether it has a deterministic
signature. It writes the memory file, puts one line in the right home, builds and proves
the gate when one is earned, runs the audit and pushes. It reports what became mechanical
and anything left as judgment, with why no detector can exist.

## Propagation runs itself

An edit to `global/CLAUDE.md` starts the rules sync from a PostToolUse hook
(`scripts/hooks/sync-rules-on-edit.sh`). The sync writes the rules into every code lane,
defers the commit where a session is open and never touches a repo published to an outside
reader. See [`rules-sync-and-shared-repos.md`](rules-sync-and-shared-repos.md).
