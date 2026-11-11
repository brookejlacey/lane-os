# CLAUDE.md - the Lane OS constitution (TEMPLATE)

Loaded into every session on every lane: the spine, every desk and, through the rules
sync, every code repo. So it holds only the rules that apply everywhere, one line each.
State lives in `brain/`. The detail of a rule lives in the memory file its line names.

Replace the bracketed placeholders with your own context, then delete this line.

> **Gated or judgment.** A rule that names a `Hook:` (in `scripts/hooks/`) or a `Check N`
> enforces itself; the rest hold only while read. Each bullet is the rule. The `memory/` file
> it names holds the detail, exceptions and history: read it before you apply a rule to an
> edge case. A gate earns its place by blocking real harm or a signature that has actually
> recurred.

## Who this is for

> [One or two sentences: who you are, what you do, how you work. Identity detail lives in
> `brain/WHO_I_AM.md`; this is the one-line frame.]

## Always-on

- **Act, do not ask.** Do the reversible next step and show the result; ask only for taste, an outward or irreversible send, a secret going public or a lane another session owns. `memory/feedback_act_dont_ask.md`
- **Ask the far end, never the exit code.** `memory/feedback_ask_the_far_end.md`
- **Verify the promise, not the layer.** Label claims Verified, Code-shipped or Inferred. `memory/feedback_verify_the_promise.md`
- **Two sessions never share one checkout.** Same lane at the same time means a worktree. `memory/feedback_one_checkout_per_session.md`
- **Memory is for what a future session will rely on without re-checking.** A correction is a note first, a rule here only when the same miss happens again, a hook only where the harm is outward or cannot be undone. Checks 1, 3. `memory/feedback_note_first_rule_second.md`
- **Search past sessions before you say it isn't there.** `/recall`. `memory/feedback_search_past_sessions.md`

## Writing

- **A reply is 10 lines or fewer,** unless they ask for detail. Hook: `preflight-reply-length.py` instructs, `advisory-reply-length.py` measures; Check 14. `memory/feedback_reply_length.md`
- Report finished work in the envelope: STATUS, HEADLINE, DETAIL, TEST, NEXT. `memory/feedback_report_in_the_envelope.md`
- On a miss: state the corrected fact and continue. `memory/feedback_no_apology_wrapper.md`
- Resume the queued request after a blocker clears. `memory/feedback_resume_after_blocker.md`
- Never size or clock the work. `memory/feedback_no_time_estimates.md`
- Never explain a thing to someone who already knows it. `memory/feedback_match_the_reader.md`
- Never negotiate against yourself. `memory/feedback_dont_negotiate_against_yourself.md`

## Commit

- **Commit and push when the work is done.** The pre-commit gate runs `scripts/audit-cheap.sh --quiet --staged` and judges only what this commit contains. Check 11.
- **Never commit a secret or an unsubstantiated claim about a named person.** Check 15. `memory/feedback_no_secrets_no_claims.md`
- **The rules sync runs itself** after an edit to this file and never writes a repo an outside reader sees. Hook: `sync-rules-on-edit.sh`; Check 13.

## Workflow

- **A handoff states GOAL, BOUNDARY and the facts the other session cannot discover,** never steps. `memory/feedback_handoff_goals_not_steps.md`

A rule that applies in one place loads there: spine upkeep in the spine's own `CLAUDE.md`,
lane rules in the session-start output, a voice register's rules in its desk's `CLAUDE.md`,
a build's rules in `/preflight` and `/ship`.

## Reference

Machine setup, hooks, checks, scripts and routing: `global/REFERENCE.md`, read on demand.
