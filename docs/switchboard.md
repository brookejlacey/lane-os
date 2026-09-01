# The switchboard: what the other windows are doing

The write-lane invariant keeps sessions from writing into each other. It says nothing
about reading. The switchboard is the read side: a per-machine, gitignored map of every
lane, so a session in one window can see what moved elsewhere without any lane writing
into another.

```bash
python3 scripts/build-switchboard.py
# switchboard/SWITCHBOARD.html   a row per lane
# switchboard/state.json         {built, built_human, lanes: {name: {head, ts, subject, focus, kind}}}
```

The SessionStart hook refreshes it in the background on every session start and prints
one pointer line to it. Run it on a schedule too if you have a machine that stays on.

## Two things it does beyond `git log -1`

**Freshness is measured on the newest non-bot commit.** The rules sync touches every
lane whenever the constitution changes. Without this filter each sync lights up "moved
<24h" on lanes nobody has opened in weeks, which is exactly the signal the page exists to
carry. `BOT_SUBJECTS` is deliberately conservative: under-filtering costs a stale-looking
row, over-filtering hides real work.

**Each lane carries a `focus`.** "What landed here" is the last commit. "What is this
lane chewing on" exists in a session or a STATUS note before it is ever a commit, and it
is the thing a neighbouring session actually needs. The builder reads the newest dated
`## YYYY-MM-DD ...` heading out of the lane's spine-facing state file
(`projects/<name>/STATUS.md`, or `desks/<name>/LOG.md`). Zero adoption cost: dated
headings already exist in most STATUS files, and an undated heading is a section label
that reports nothing, so it is ignored.

## The rule it serves

**Ask the neighbouring lane before re-deriving what it already knows.** Overlap between
what you are about to do and another lane's `focus` means message that session (or drive
it: `cd <repo> && claude -p "<goal>"`), never a write into its lane.

## Configuration

`LANE_OS_WORKSPACE_ROOTS` (colon-separated) names the directories that hold code repos;
default `~/repos:~/work`. Desks are read from the spine. The spine itself is skipped. A
lane with no human commit in 14 days is shown as idle, not removed: archiving is a
deliberate move.
