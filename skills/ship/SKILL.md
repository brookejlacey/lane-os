---
name: ship
description: The one-command "ship a change" workflow. Read the deviation log, clean up the diff, run the project's own verification gates for the change type, drive the UI when UI changed, declare Verified vs Code-shipped vs Inferred, then commit and push (and open a PR and watch CI where the repo uses them). Composes existing built-ins rather than reinventing them. Trigger on "/ship", "ship this", "ship it", "this is done".
---

# /ship

Hand off as much of "is this really done?" to the agent as possible, so nothing ships
on an inferred "should work". This skill does not reinvent verification. It orchestrates
what the project already has, and runs each project's own `TESTING.md` gates. Run it
from inside a code lane when a change feels done.

Two layers: a **verification layer** that runs while building (does it work, did it
regress anything), and an **independent review** by a second agent with no shared
context, before merge. `/ship` runs the first fully and offers the second.

## Steps

1. **Scope the change, and read the deviation log first.** `git status`, `git diff`,
   `git diff --stat`. Classify: UI, backend or API, contracts, mobile, schema, docs-only.
   Docs-only or config-only skips to step 5 and says no functional gates applied.

   If `implementation-notes.md` exists at the repo root (seeded by `/preflight`), read
   it before anything else. Its `## Deviations` section is the list of judgment calls
   the build made alone; every one is a candidate gate in step 3 and a candidate line in
   the honest labelling in step 5. A deviation is precisely the thing the diff looks fine
   about. Once its contents are folded into the report and the lane's `STATUS.md`,
   **delete the file**. It is build-scoped scratch, not durable state.

2. **Clean up the diff.** Run the project's simplify or lint pass (reuse, dead code,
   altitude). Apply its fixes. Do not run the review layer here; that is step 6.

3. **Pick the gates from the project's own spec.** Read `TESTING.md` at the repo root if
   present; it is the authoritative change-type to gates table. Without one, infer from
   the stack: typecheck, lint, build, always, when the repo has the script; the test
   suite for the touched area; a deploy plus a re-drive of any UI that calls a changed
   backend; the simulator for mobile before any store upload.

4. **Drive the UI.** For any frontend change, exercise it as a user: start the dev
   server, open the page, click through the changed flow, read the console, capture a
   screenshot. Report regressions you notice even when unrelated to the task. UI changes
   also get a design check against the project's own style guide.

5. **Declare honestly, then commit and push.** Label the result: **Verified** (ran the
   live check, watched the expected behavior), **Code-shipped** (committed but not yet
   runtime-verified, say why), or **Inferred** (reasoned, not run, flag it). Anything
   still open in the deviation log is Inferred by definition. Then commit and push
   through the commit gate. `STATUS.md` updates ride along.

6. **Offer the independent review.** For a non-trivial or user-facing change, offer a
   second-agent code review before or after the PR. If the repo uses PRs and CI: open the
   PR, watch CI, fix failures as they land. If it auto-deploys from push, say so and skip
   the PR ceremony.

## Rules

- Compose, do not reinvent. Prefer the existing skill or script over a hand-rolled check.
- `TESTING.md` is the source of truth for which gates apply. The inference list is only
  the fallback.
- Never claim Verified for something you only Inferred. If a gate could not run (no
  simulator, no credentials, environment down), say Code-shipped or Inferred and name
  the missing step. This is the whole point.
- Do not gate-creep. Run the gates for what changed, not every gate.
- Commit and push is part of shipping, not a separate ask.
- Report in the envelope: STATUS, HEADLINE, DETAIL, TEST, NEXT. One HEADLINE line for a
  small change.
