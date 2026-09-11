# The voice layer: rules drift, a corpus does not

Ask for a voice and you will describe it: warm but direct, professional but human,
confident not arrogant. Every writer alive would sign those adjectives, so the model
returns the average of everyone who ever claimed them, and that average IS the
corporate-brochure register. Describing a voice cannot escape it. The description is
the problem.

The fix is two files doing two different jobs, and the split is the whole insight.

| | Holds | Good at | Fails by |
|---|---|---|---|
| `VOICE.md` | Short distilled rules: a "sound like" list and a longer "never sound like" list | Being read in two seconds and enforced by a linter | Drifting, because it is somebody's summary of a voice rather than the voice |
| `corpus/` | Unedited real samples of the person's actual writing, stored as dated pulls, every old pull kept | Being the thing itself, so it cannot be averaged away | Going stale, which is why it is re-pulled rather than cleaned |

The never-list does more of the work and is far easier to write, because "not that" is
observable and "warm but direct" is not. The corpus is what the rules are checked
against. Neither substitutes for the other, and a register with only one of them
produces exactly the draft this layer exists to prevent.

## Three things the corpus teaches that nobody guesses

- **Replies matter more than posts.** A composed post is the edited voice. A reply is
  the actual one. A corpus of published work alone still produces a stiff draft.
- **Spoken transcripts are a separate register from typed text.** Mixing them produces
  a draft that is neither, so `corpus/typed/` and `corpus/spoken/` stay apart and the
  target medium picks one.
- **Cleaning up a sample deletes the exact thing being captured.** The dropped word,
  the lowercase start, the run-on: that is the fingerprint. Raw or nothing.

## The instruction that changed the output more than any other

It lives in the register's own `CLAUDE.md`, not in a chat message, so every session
there gets it:

> Before writing a line, open `corpus/` and read five to ten real samples in the same
> register as the thing about to be written. Match those samples. Do not match an idea
> of what professional sounds like. If nothing in the corpus fits the register, say so
> and ask for a sample instead of guessing.

## The linter

A model asked to review its own prose is the same model that wrote it, so self-review
misses the same things every time, in the same direction. `scripts/check-voice.py` runs
thirteen checks that cannot be talked out of it. All mechanical: count, match, compare.

```bash
python3 scripts/check-voice.py desks/<register>/outbox/draft.md
python3 scripts/check-voice.py --list          # the thirteen, one per line
python3 scripts/check-voice.py --self-test     # each one on its positive AND its negative
```

| Check | Fires on |
|---|---|
| `em-dash` | An em-dash or horizontal bar, anywhere |
| `ai-tell-word` | A word from the tell list, plus every backticked term in the register's never-list |
| `rhetorical-close` | The draft closes on a question |
| `staccato-run` | Three or more short sentences back to back, quotation fragments exempt |
| `cadence-flat` | A short median with no sentence long enough to be a build |
| `no-comma-splice` | A long draft with zero comma splices, which no person writes |
| `contractions-low` | Contraction density under the writer's own floor: reads assembled |
| `contractions-high` | Contraction density over the writer's own ceiling |
| `comma-before-and` | The rate, printed every run, flagged outside the writer's own range |
| `person-balance` | The first-to-second-person ratio, printed every run, flagged when an instructional draft's subject is the writer |
| `post-too-long` | A post over the target platform's character limit |
| `thread-too-long` | A thread over the target platform's post limit |
| `unchecked-claim` | A price, stage or customer claim with no `checked:` marker |

Two of them print their number on every run, passing or failing. Slow drift is
invisible to a check that only speaks on failure.

### The thresholds come from the corpus, not from a style guide

Contraction density and comma rate are one writer's fingerprint, not a virtue. An
absolute threshold would push every writer toward the same middle, which is the failure
being fixed. So the ranges are measured from the register's own samples:

```bash
python3 scripts/check-voice.py --measure desks/<register> --write
```

That writes the `[measured]` block in the register's `voice.toml`. A register with no
measured block gets a `not-measured` notice, never a silent pass, and Check 17 warns
when a corpus pull lands without a re-measure.

### The pattern worth copying: demand a marker, never guess

Claims about a product's price, stage or customers are not this layer's to make, and
the linter has no way to know the answer. It does not guess and it does not stay
silent. It requires the draft to carry a marker proving a human checked:

```markdown
---
medium: thread
checked: price, customers
---
```

Whenever a check cannot know the answer, demand the marker instead.

## Two rules the layer depends on

- **A new check ships as a warning.** It becomes a blocking failure only after it has
  passed on real work with no false positive, and the promoting commit says how many.
  A gate that cries wolf teaches the next session to bypass every gate, including the
  ones that were right. Check 17 is a WARN today for exactly this reason; Check 16, the
  linter's own self-test, is a FAIL, because a check that has stopped firing looks
  identical to a clean draft.
- **Scope a prose check to the changed files.** A corpus-wide retrofit on day one
  buries the signal under a hundred findings nobody asked for, and the check gets
  switched off. Check 17 reads `changed_paths`, the same scoping the commit gate uses.

## Why this belongs in Lane OS

A voice is not one voice. The same person writes in several registers, with different
consequences for getting each one wrong, so each register gets its own folder, its own
corpus and its own never-list:

```
desks/<register>/
├── CLAUDE.md      the contract: read five to ten samples first, and the posture
├── VOICE.md       sound like / never sound like; backticked terms are enforced
├── voice.toml     [target] authored, [measured] written from the corpus
├── corpus/
│   ├── typed/     posts-YYYY-MM-DD.md, replies-YYYY-MM-DD.md
│   └── spoken/    transcript-YYYY-MM-DD.md
├── outbox/        drafts, linted before a human reads them
└── LOG.md         the running record
```

That is a desk, so it inherits the whole invariant: a session opened in one register
cannot answer in another's voice and cannot edit another's files, and the guard blocks
it rather than the model remembering. This is the write-lane invariant applied to
writing rather than to code, which is the reason the voice layer belongs here and not
in a standalone prompt-engineering note.
[`docs/write-lane-invariant.md`](write-lane-invariant.md)

## Standing one up

```bash
scripts/new-lane.sh voice <register>              # from desks/_TEMPLATE-voice/
$EDITOR desks/<register>/CLAUDE.md desks/<register>/VOICE.md
# pull raw samples into desks/<register>/corpus/typed/ and corpus/spoken/
python3 scripts/check-voice.py --measure desks/<register> --write
```

Then open a session in `desks/<register>/` and write. The template ships with the four
corpus rules in `desks/_TEMPLATE-voice/corpus/README.md`, which is the file to read
before the first pull.
