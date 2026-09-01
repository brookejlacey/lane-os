---
name: preflight
description: The start-of-build counterpart to /ship. Runs the five build-preflight gates plus three unknown-reduction moves (a blind-spot pass, a bounded architecture interview, an implementation plan ordered by what will change), then seeds the deviation log the build writes into. Use when a non-trivial build is about to start, or on "/preflight", "spec this before we build", "what am I missing", "interview me about this". Run it unprompted at the first sign of "we're building X".
---

# /preflight

`/ship` closes a build. This opens one. It exists because the five gates were prose the
model had to remember, and the thing that keeps failing is remembering, not knowing.

**The premise:** with a strong model, output quality is bottlenecked by how well the
unknowns are clarified, not by the model's ability to write code. An unknown is any
decision the build has to make that the prompt does not settle. This skill converts
unknowns into either a stated decision or a logged deviation, so nothing is silently
guessed.

## When to run

- Any build beyond a quick edit: new repo, product surface, feature, script, doc system.
- Unprompted at the first sign of "we're building X". Skipping it is the failure mode.

## When not to run

- A quick edit, a copy tweak, a one-liner, a change to code that already exists.
- The human is thinking out loud with no deliverable requested. Co-author instead.

## Step 0: name the territory before you scout it

The unknowns live wherever the build's reality lives, and that is not always the code:

| Build shape | Where the unknowns actually are |
|---|---|
| Feature inside a mature codebase | The codebase: conventions, call sites, modules nobody has read |
| Greenfield in a domain the human knows | Mostly the spec; run the gates light |
| Greenfield in a regulated or counterparty domain | The domain and the counterparty, not the code |
| Integration with a third party | Their API's real behavior, auth, rate limits, failure modes |

Say in one line which territory this build's unknowns live in, then aim everything
below at it.

## Step 1: blind-spot pass (unknown unknowns)

Ask, in that territory: what would someone who has done this before know that the human
has not said? Produce the decisions this build will be forced to make that the prompt
does not settle. Questions, never asserted constraints; an unresolved unknown stays a
question. Rank by what changes the architecture if the answer flips. Route the ones that
need an outside human to a commitments list rather than guessing.

Then **gate 5, instrument-class fit:** if the human's own word for the thing does not
match what the hard details point at, reconcile now. Their word is a spec.

## Step 2: prior art and system fit (gates 1 and 2)

- **Gate 1, prior art:** is this a moat (build) or a commodity (scout, default to adopt)?
  Report adopt, adopt-with-wrapper, reference (read an existing implementation for its
  semantics without taking the dependency), or build.
- **Gate 2, system fit:** does this belong in an existing lane, skill or repo rather than
  a new one? Does it contradict a convention? Fixing the class or the instance?

## Step 3: interview (known unknowns), bounded

Ask the human **one question at a time**, only about things where the answer changes the
architecture. **Cap: five questions**, then build with stated assumptions. This is a
deliberate, narrow carve-out from act-do-not-ask and loosens it nowhere else: if a
question can be answered by reading the repo, the brain files or the live source, it is
not an interview question. Skip the interview entirely when nothing architecture-changing
is open.

## Step 4: prototypes, only when taste is the unknown

When the unknown is visual or interaction taste, render 3-4 genuinely different options
on one page for the human to react to instead of asking.

## Step 5: implementation plan, ordered by what will change

1. Data model: tables, fields, required vs optional, what is PII.
2. Type interfaces and contracts: the shapes crossing boundaries.
3. Anything user-facing: copy, flow, states.
4. Everything else.

A plan that opens with the file tree buries the only parts worth reviewing. State
**gate 3** (anticipate the real spec: the failure path, the obvious next needs,
verify-the-promise end to end) and **gate 4** (pre-mortem by inversion: assume it
shipped and failed, say what killed it, plus what you are assuming).

## Step 6: seed the deviation log

Before the first file, create `implementation-notes.md` at the repo root with a
`## Deviations` heading, and hold this contract for the whole build:

> When an edge case forces a deviation from the plan, pick the conservative option, log
> it under Deviations with the reason and the alternative, and keep going. Do not stop
> to ask. Do not silently absorb it.

At ship time the Deviations list IS the Inferred column. `/ship` reads it, folds it into
the report and the lane's STATUS, and deletes it. It is gitignored in this scaffold.

## Output

Post the preflight before the first file. Six lines is a pass:

```
Territory: <where the unknowns live>
Blind spots: <top 2-3 architecture-changing unknowns, ranked>
Prior art: <verdict + one-line why>
Fits: <existing lane/skill/repo, or why new>
Spec incl. extras: <the promise + the obvious next needs>
Killed it: <the pre-mortem failure mode being designed against>
```

Then interview only if there are real forks, then build. The preflight is not asking
permission. It is doing the thinking, then executing.

## Guardrails

- Timebox it. This is a gate, not a research project.
- Never manufacture a constraint to fill a blind spot.
- Honor the write-lane invariant: a code lane writes its repo and `projects/<name>/`.
- The interview cap is real.
