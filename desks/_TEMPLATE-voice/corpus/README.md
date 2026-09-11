# corpus - the raw record of how this person actually writes

The rules in `VOICE.md` are a summary and they drift. These files are the voice itself.
Neither one substitutes for the other.

## Four rules, all of them load-bearing

1. **Raw or nothing.** Do not fix a typo, expand an abbreviation, restore a dropped
   word or tidy the punctuation. The mess IS the fingerprint; cleaning a sample deletes
   the exact thing being captured.
2. **Replies outrank posts.** A composed post is the edited voice. A reply is the
   actual one. A corpus of published work alone still produces a stiff draft, so pull
   replies first and keep more of them.
3. **Typed and spoken never mix.** A transcript is a different register from typed
   text, and a draft built from both is neither. `typed/` and `spoken/` stay apart, and
   the target medium picks one.
4. **A pull is dated and kept forever.** Stale means pull again, never edit in place.
   Every old pull stays, so the record is longitudinal and you can see the voice move.

## Layout

```
corpus/
├── typed/     posts-YYYY-MM-DD.md, replies-YYYY-MM-DD.md, messages-YYYY-MM-DD.md
└── spoken/    transcript-YYYY-MM-DD.md
```

One pull per file, named for what it holds and the day it was taken. Inside a file,
one sample per block, separated by a blank line. No commentary between samples.

## After a pull

```bash
python3 scripts/check-voice.py --measure desks/<register> --write
```

That reads these files and writes the `[measured]` block in the register's
`voice.toml`, which is where the linter's thresholds come from. Ranges that came from
anywhere else are a style guide wearing a number.

The band is the mean across pulls plus or minus one standard deviation, so two pulls
give a jumpy range that a third will move a lot. Pull until it stops moving.
