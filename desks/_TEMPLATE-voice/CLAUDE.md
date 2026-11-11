# _TEMPLATE voice register - contract

This desk owns one register of one person's writing. A session here reads THIS file
first, then five to ten real samples from `corpus/`, then `VOICE.md`. It does NOT load
the whole brain, and it does NOT answer in another register's voice.

## The instruction that does the most work

Before writing a line, open `corpus/` and read five to ten real samples in the SAME
register as the thing about to be written. Match those samples. Do not match an idea of
what professional sounds like, and do not match `VOICE.md` alone, which is a summary.
If nothing in the corpus fits the register, say so and ask for a sample. Never guess.

## Why two files

Describing a voice cannot escape the average. Warm but direct, professional but human:
every writer alive would sign those, so the model returns the average of everyone who ever
claimed them, which is the corporate-brochure register. `VOICE.md` holds the distilled
rules, a "sound like" list and a longer "never sound like" list that does most of the
work. `corpus/` holds unedited real samples as dated pulls. Rules drift because they are
somebody's summary of a voice; the corpus does not. These rules load here, in the
register's own desk, not in every session. Full: `docs/voice-layer.md`.

## Reading order
- `corpus/typed/` for anything typed. `corpus/spoken/` for anything spoken aloud.
  They are different voices; a draft built from both is neither.
- Inside a pull, replies outrank posts. A composed post is the edited voice; a reply is
  the actual one.
- `VOICE.md` second, for the never-list.
- A corpus sample is stored raw. Cleaning one up deletes the exact thing being captured.
  Stale means re-pull, never edit. The linter's thresholds are measured from the corpus,
  so Check 17 warns when a pull lands without a re-measure.

## Posture
- [What this register is for, and who reads it. What is out of scope.]
- [What getting it wrong costs here. That cost is why this register is its own lane.]

## Write lane
- Write only under `desks/_TEMPLATE/` and `brain/drafts/`. Nothing else, even if asked.
- Another register's corpus and never-list are another lane. Do not read across to
  borrow a phrase; the whole point of the split is that the registers differ.

## Drafting
- Finished drafts go in `outbox/`, one file each, with front matter naming the medium.
- Run the linter before a human reads it: `python3 scripts/check-voice.py <draft>`. A model
  reviewing its own prose misses the same things every time. Check 16 proves the checks
  still fire; Check 17 runs them on changed drafts.
- Claims about price, stage or customers are not this desk's to make. Get them from
  the lane that owns them, then record the `checked:` line naming what was verified.

## Data sources
- [Where the corpus pulls come from, and the command that pulls them.]
