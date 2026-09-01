# The reply-length gate: measure after, instruct before

Every other hook gates a tool call. Sort a session's rule misses by where they happened
and most are reporting failures, not doing failures: the execution layer held (the lane
guard fired, the commit gate blocked) and the reply drifted, because nothing watches the
reply. This pair does.

## Why two halves

A Stop hook fires after the reply exists and has been paid for. Anything it says can only
be acted on by a second reply, which either restates the answer (rendering the same fact
twice) or spends a turn saying nothing. A Stop hook can measure drift. It cannot prevent
the reply it measures.

| Hook | Event | Does |
|---|---|---|
| `scripts/hooks/advisory-reply-length.py` | Stop | Reads the transcript, counts the prose words of the final assistant message (fenced blocks excluded), notes self-narration, appends one JSON row to `outputs/reply-length.jsonl`. Says nothing. |
| `scripts/hooks/preflight-reply-length.py` | UserPromptSubmit | Reads that log for this session. Once 2 of the last 4 real replies ran over the limit, or one narrated its own process, injects one line of context before the next reply. Otherwise silent. |

That conditioning is the point. The rule already lives in the always-loaded
constitution, so a reminder on every turn buys nothing but tokens; what decays is
adherence deep into a long session. A well-behaved session costs zero tokens; a drifting
one costs one line, delivered where it can still change the output.

## The shared contract

Both files carry the same `WORD_LIMIT` (220, generous: the rule says about 10 lines; this
catches a wall) and the same carve-outs:

- an explicit ask for detail in the prompt ("detailed", "walk me through", "deep dive",
  "long form") lifts the cap with no pushback;
- a long-form desk, named in `LANE_OS_LONG_FORM_DESKS` (comma-separated desk names), is
  standing-lifted.

Two halves of one rule that disagree about when the rule applies are worse than either
alone, so `audit-cheap.sh` Check 14 asserts the constants still match and both
`--self-test` runs pass.

## What it logs

```json
{"ts": "...", "session": "...", "words": 312, "findings": 1, "kinds": ["reply is 312 words"]}
```

Kinds, not just a count, so the pre-check can say which habit is drifting. Replies under
25 words are acknowledgements and are excluded from the window, so a long/short
alternation cannot hide real drift. `outputs/` is gitignored; it is a per-machine
measurement, not state.

## Debugging

`REPLY_LENGTH_ADVISORY=1` makes the Stop half print its findings again. Self-tests:

```bash
python3 scripts/hooks/advisory-reply-length.py --self-test
python3 scripts/hooks/preflight-reply-length.py --self-test
```
