# Gated or judgment: which rules enforce themselves

Every rule line in the constitution is in one of two states.

| State | Meaning | How it fails |
|---|---|---|
| **Gated** | The line names a `Hook:` or a `Check N`. A hook fails the tool call; a check fails the commit. | It cannot be forgotten. It can only be removed, and removing it is visible in the diff. |
| **Judgment** | No gate. It holds while it is loaded and read. | Quietly. That is why the files that load it stay short. |

The line is the rule. The memory file it names holds the detail, the exceptions and the
history, so the loaded file stays one line per rule.

## A gate earns its place

There are two reasons to build a gate:

1. **The harm is outward or cannot be undone.** A secret reaching a public surface, an
   outward send, a write into another lane's files, a repo shared with the wrong reader.
2. **The same miss has actually recurred** and it has a deterministic signature: the same
   class of miss more than once, or a constraint dropped across rewrites of one artifact.

Everything else stays a judgment rule. That is not a lesser outcome. A detector that fires
on the wrong things gets switched off, which is worse than no detector, because the next
session learns that gates are noise and bypasses the ones that were right.

## The ratchet and why it was retired

An earlier version of this scaffold opened the constitution with a measured line,
`Coverage today: N of M bullets are gated`. A script counted the gated rules. A triage file
recorded the ones that could not be gated, with the reason. A commit check failed when
the line and the file disagreed or the untriaged count grew. The idea was that the decay
surface becomes a list you work down.

What it did in the spine this came from: every miss became a new always-loaded rule plus a
check, because the count rewarded it. The always-loaded rules went from 51 lines in July to
103 in November. The guidance for Claude Code instruction files is to keep them short,
since every added line competes with the rest for the model's attention, so the ratchet was
growing the very file it was meant to protect. On November 10, 2026 the counter, the triage
file and the check were retired together. No hook was retired with them.

What replaced it is an order, not a count: a correction is a note first. It becomes a
loaded rule only when the same miss happens a second time. It gets a hook only for the
first reason above. [`miss-to-rule-loop.md`](miss-to-rule-loop.md) has the full loop.

## Where a gate lives

A **hook** (`scripts/hooks/block-*.py`, PreToolUse) when the wrong thing should never
reach disk: it sees the tool call and exits 2. A **check** (a `section` in
`scripts/audit-cheap.sh`) when the wrong thing is visible in a diff: it fails the commit.
Either way the rule's line names it (`Hook: block-cross-lane-write.py`, `Check 9`), so a
reader of the rule can find what holds it.

## A gate may retire

A gate that has blocked nothing real in a long window costs every session something and
protects nothing. Count its real blocks in the session transcripts (its block message,
searched with `rg` under `~/.claude/projects/`) and let a spine session decide from the
count. The outward-harm gates never retire on a count: one real block is the whole reason
they exist.

## A fail-open guard cannot report its own death

A PreToolUse guard should fail open: a false block stops real work, so uncertainty exits
0. But that means a broken guard and an approving guard are byte-identical from outside.
Silence means both "allowed" and "I crashed". So every fail-open guard needs a self-test
that asserts it still BLOCKS, run where nobody has to remember it:

- `scripts/test-lanes.sh` feeds the write-lane guard 25 representative writes and
  asserts the exit code in both directions (over-blocking is its own outage).
- Check 9 runs it on every commit.
- The reply-length pair, the budget table, the probe runner and the rules-sync hook each
  carry the same kind of test (`scripts/tests-*`, `--self-test`). Each was verified by
  reintroducing the bug and watching the test go red.

When you build a gate, prove it blocks: plant the violation, watch PASS turn to FAIL,
remove it, watch PASS return. Assert behavior, never loadability.
