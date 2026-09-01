# The miss-to-rule-plus-check loop

A found miss gets four things, in order, and an apology is not one of them:

1. **The instance fixed.**
2. **The rule written in its durable home**: a `memory/feedback_*.md` file with the scar
   attached (what actually went wrong, in the human's words where they said it), a
   pointer in `memory/MEMORY.md`, and one bullet in `global/CLAUDE.md` if it is
   always-on.
3. **A gate wired** when the signature is deterministic: a hook or an `audit-cheap`
   check, proven to block.
4. **The bullet naming the gate**, and the coverage line restated from the measured
   number.

"Sorry, I'll be more careful" is a non-fix: the same failure returns next session because
nothing in the system changed. The only acceptable response to a miss is a structural
one.

## Fix the class, not the instance

When a process failure surfaces, add the tripwire that catches the whole category. A
draft that rotted for a day became Check 6 (any draft older than 7 days). A guard that
silently approved everything became Check 9 (assert it blocks, every commit). A hook that
existed but was registered nowhere became Check 10. Each of those was one embarrassment
turned into a permanent detector.

## A caught output defect adds the missing assertion

If the human finds a property wrong after every existing check passed, encode that
property in the verifier. A green check proves only the shape it encodes; when a
property is wrong while its check is green, find the shape the check cannot see and add
the distribution-level assertion instead of tightening an unrelated threshold.

## The real trigger for a check is revision-survival

Across one session that rewrote a single artifact four times, every rule with a check
held and got fixed inside the same turn; every rule living only in prose decayed
silently, because each rewrite re-derives the artifact from the newest instruction and
drops constraints set two rewrites earlier. A rule carried forward through N rewrites
has a decay rate; a rule that runs as a check does not. So: anything restated across
multiple drafts of one artifact needs a check, whatever its signature. Code lanes get
this for free (compiler, tests); prose lanes do not, and need it built.

## A countable rule prints its count on every run

A check that only speaks on failure leaves slow drift invisible until it trips a
threshold. `INFO · gated-rule coverage: 12 of 28 (42%)` on a passing run is the point.

## How `/reflect implement` runs it

`skills/reflect/SKILL.md`, implement mode. Per learning it asks one question: does this
have a deterministic signature? Yes: build the gate (scoped to changed files for anything
prose-shaped, tuned until precise, honest when it cannot run, with an escape hatch),
prove it blocks, land the memory file, name the gate on the bullet, restate coverage,
sync the rules, run the audit, push. No: one row in `global/rule-triage.tsv` saying why
no detector can exist. Then report what became mechanical, not what was learned.

## Propagate, always

A rule that lives in one repo is not a rule. After any edit to `global/CLAUDE.md`, run
`python3 scripts/sync-rules.py`. It writes the rules into every code lane, defers the
commit where a session is open, and never touches a repo published to an outside reader.
See [`rules-sync-and-shared-repos.md`](rules-sync-and-shared-repos.md).
