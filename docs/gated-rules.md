# Gated or judgment: rules that enforce themselves

Every rule in the constitution is in one of three states, and the difference is the
whole design.

| State | Meaning | How it fails |
|---|---|---|
| **Gated** | The bullet names a `Hook:` or a `Check N`. A hook fails the tool call; a check fails the commit. | It cannot be forgotten. It can only be removed, and removing it is visible. |
| **Judgment** | Recorded in `global/rule-triage.tsv` as having no deterministic signature, with the reason. | It holds only while it is loaded and read. That is the honest state of a rule about conversation. |
| **Untriaged** | Nobody has decided which of the above it is. | Silently. This is the decay surface, and it is the work queue. |

## Why this is the load-bearing idea

Rules held only in prose decay, and only those do. Measured over four months in the
spine this scaffold came from: the two always-loaded files with a byte ceiling were flat
or smaller; the two governed only by a written brevity rule had grown 2x and 5.2x. A
write-lane guard had been approving every write for weeks behind a bare `except`. A
rule about decorative numbers stopped applying because its scope said one document kind
and the document was another. None of that was carelessness. Every one was a rule
nobody had made mechanical.

So the constitution opens with its own coverage:

> Coverage today: N of M bullets are gated.

That line is measured, never hand-typed. `scripts/find-decayed-rules.py --count` prints
`gated judgment untriaged`; `scripts/audit-cheap.sh` Check 12 fails the commit when the
claim and the file disagree. Restating it downward means naming which gate was removed
and why. That is the ratchet.

## The tools

```bash
python3 scripts/find-decayed-rules.py              # the full report
python3 scripts/find-decayed-rules.py --untriaged  # the work queue, with each rule's key
python3 scripts/find-decayed-rules.py --count      # "gated judgment untriaged"
```

`global/rule-triage.tsv` holds one row per judgment rule: `<key>\tJUDGMENT\t<why no
detector can exist>`. The key is derived from the bullet's first bolded phrase; the
`--untriaged` report prints it for you. JUDGMENT is not an excuse. A detector that fires
on the wrong things gets disabled, which is worse than no check, so each row says why.

## What counts as a gate

A **hook** (`scripts/hooks/block-*.py`, PreToolUse) when the wrong thing should never
reach disk: it sees the tool call and exits 2. A **check** (a `section` in
`scripts/audit-cheap.sh`) when the wrong thing is visible in a diff: it fails the commit.
Both are named on the rule bullet (`Hook: scripts/hooks/x.py`, `Check 9`), which is what
`find-decayed-rules.py` reads.

## A fail-open guard cannot report its own death

A PreToolUse guard should fail open: a false block stops real work, so uncertainty exits
0. But that means a broken guard and an approving guard are byte-identical from outside.
Silence means both "allowed" and "I crashed". So every fail-open guard needs a self-test
that asserts it still BLOCKS, run where nobody has to remember it:

- `scripts/test-lanes.sh` feeds the write-lane guard 25 representative writes and
  asserts the exit code in both directions (over-blocking is its own outage).
- Check 9 runs it on every commit.
- The reply-length pair, the budget table and the probe runner each carry the same
  kind of test (`scripts/tests-*.py`, `--self-test`), and each was verified by
  reintroducing the bug and watching the test go red.

When you build a gate, prove it blocks: plant the violation, watch PASS turn to FAIL,
remove it, watch PASS return. Assert behavior, never loadability.

## Adding a rule

1. Write the bullet in `global/CLAUDE.md`, starting with `- **Bold key.**`.
2. Ask: does this have a deterministic signature? Yes: build the gate and name it on the
   bullet. No: add a row to `global/rule-triage.tsv`.
3. `python3 scripts/find-decayed-rules.py --count`, restate the coverage line.
4. Commit. Check 12 confirms the numbers; the untriaged count must not have grown.

`/reflect implement` walks exactly this loop from a session's learnings. See
[`miss-to-rule-loop.md`](miss-to-rule-loop.md).
