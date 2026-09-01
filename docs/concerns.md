# Concerns that declare how they close

`brain/CONCERNS.md` is the only brain file that holds "we do not know yet". Every item in
it names the event that closes it. In most systems nothing ever checks whether that
event has happened, so items leave the file only when a human happens to re-read it. In
the spine this came from, that meant three items marked RESOLVED still sitting in the
open list, one warning about a ceiling cut a week earlier, and a file that had grown
5.2x, mostly on that.

The fix is not discipline. It is that a concern must declare how it gets checked.

## The contract

Every item under `## Right Now` declares one of:

```markdown
**Probe:** `<shell command>`
**Owner:** you
**Owner:** the alpha lane
```

- A **Probe** is a command the machine runs on a schedule. It prints one line starting
  `CLOSED`, `OPEN` or `UNKNOWN`. `scripts/probe-concerns.py` runs it and stamps the
  result with the date.
- An **Owner** is the one human or lane who can close it, because no command can observe
  the closing event. `you` (or `LANE_OS_HUMAN`) means a decision only the human can
  make: put it in front of them once, then leave it alone. Any other owner is work a lane
  has to do, and should never reach the human at all.

`audit-cheap.sh` Check 8 fails the commit on an item that declares neither. Check 7 warns
on an item with no date in the last 30 days: an open concern is probed, never re-dated.

That split is the real content. The file was doing two jobs, an open unknown that
evidence closes and a decision someone owes, and both decayed the same way. The probe
report separates them: DECISIONS OWED reaches the human, OWNED WORK does not.

## Rules for a probe

- **A probe never closes an item on its own.** It flags; a human confirms and moves the
  item to `brain/archive/` with its evidence. The first real run of this system proved
  why: a probe matched a vendor's marketing mail and reported CLOSED, and the
  confirmation step found the thing had not happened.
- **A probe observes the EVENT, never the FILING.** `grep DECISIONS.md` asks whether the
  decision was written down, not whether it was made, so the only thing that can close
  it is the act of closing it. Point the probe at a transcript, a customer record, a live
  endpoint, a branch.
- **A probe that cannot run says UNKNOWN, never OPEN.** A probe that fails on a missing
  GNU tool or an old bash and prints nothing has measured nothing. Silence is not
  evidence. The runner treats a non-zero exit, a timeout, an empty line or an
  unrecognized first word as UNKNOWN.
- **Scope a probe to the entity it is about.** A loose match produces a false CLOSED,
  which costs the confirmation step.
- Prefer a durable source (a file, a branch, a database, a mail search) over a transient
  one.

## Running it

```bash
python3 scripts/probe-concerns.py            # run every probe, stamp the results
python3 scripts/probe-concerns.py --dry-run  # run, change nothing
python3 scripts/probe-concerns.py --check    # drift only, no probes (what Check 8 runs)
```

Output groups the items: READY TO CLOSE, COULD NOT PROBE, DECISIONS OWED, OWNED WORK,
UNDECLARED. Run it from a spine session's `/catchup`, and on a schedule if you have a
machine that stays on.

`scripts/tests-probe-concerns.py` asserts each verdict, that CLOSED never removes an
item, and that stamps replace rather than accumulate.
