# CONCERNS (TEMPLATE)

Open loops and worries, where the answer is not known yet. One test decides what
belongs here: **what event closes this?**

| closes on | goes in |
|---|---|
| evidence (a probe, a check, someone answering) | here |
| you doing a thing | a task list or the lane's STATUS.md |
| a choice already made | `DECISIONS.md` |
| nothing, it is just true | `memory/` |

Every open item declares how it closes, and `scripts/probe-concerns.py` enforces it:

- `**Probe:** \`<command>\`` prints one line starting `CLOSED`, `OPEN` or `UNKNOWN`. The
  machine runs it on a schedule and stamps the result. A probe never closes an item on
  its own; it flags, a human confirms. A probe that cannot run says UNKNOWN, never OPEN.
- `**Owner:** <who>` when no command can observe the closing event. `you` means a
  decision only the human can make; anything else names the lane that owns the work.

An item with neither can only be closed by someone noticing, which is exactly what
fails. `audit-cheap.sh` Check 8 fails the commit on it. Point a probe at the EVENT
(a transcript, a live endpoint, a branch), never at the filing of the event (a grep of
`DECISIONS.md` asks whether the decision was written down, not whether it was made).

Pruning: the "Right Now" section is pruned on every edit, never re-dated. Resolved items
move to `brain/archive/concerns-resolved.md` with their evidence. Check 7 warns on an
open item with no date in the last 30 days.

## Right Now

### 🟡 1. [Example, probed] The staging deploy has not been checked since the last dependency bump
*Opened 2026-08-31.*

Nothing has exercised the staging health endpoint since the bump. If it is down,
the first person to find out is a user.

**Closes on:** the endpoint answering 200 after the bump.

**Probe:** `curl -fsS --max-time 10 https://staging.example.invalid/health >/dev/null 2>&1 && echo "CLOSED health endpoint answers" || echo "UNKNOWN could not reach the health endpoint"`

### 🟡 2. [Example, owned] Whether the research desk should keep a reading queue
*Opened 2026-08-31.*

No command can observe this. It is a decision, and it should be put in front of the
human once, then left alone.

**Owner:** you

## Watching

Lower-urgency items you do not want to forget. Same rule: a Probe or an Owner each.
