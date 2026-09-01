#!/usr/bin/env python3
"""Run every open concern's declared probe and stamp the result.

WHY THIS EXISTS
---------------
`brain/CONCERNS.md` is the only brain file that holds "we do not know yet". Every item
in it already names the event that closes it. In the spine this was built in, nothing
ever checked whether that event had happened, so items closed only when a human happened
to re-read the file: three items marked RESOLVED still sat in the open list, one warned
about a ceiling that had been cut a week earlier, and the file had grown 5.2x on that.

The fix is not discipline. It is that a concern must declare how it gets checked:

  **Probe:** `<shell command>`   the machine checks it, on a schedule
  **Owner:** you                 only the human can close it, so it is a decision owed
  **Owner:** <lane>              a lane owns the work; no passive signal exists

A concern that declares neither is drift, and this script says so. That split is the
real content: the file was doing two jobs, and only one of them ever needed the human.

CONTRACT
--------
A probe command prints one line to stdout. The first word decides what happens:

  CLOSED   the closing event has happened; the item is flagged as ready to close
  OPEN     still open; the rest of the line is recorded as the probe result
  UNKNOWN  the probe could not reach its source (no network, no credential).
           Recorded, but never treated as evidence either way.

A probe that exits non-zero, times out, or prints nothing is UNKNOWN. A probe is
never allowed to close an item on its own: it flags, a human confirms. Silence is
not evidence.

USAGE
-----
  scripts/probe-concerns.py            run every probe, rewrite the stamps
  scripts/probe-concerns.py --dry-run  run every probe, change nothing
  scripts/probe-concerns.py --check    report drift only, run no probes (for audit-cheap)
  scripts/probe-concerns.py --file X   use X instead of brain/CONCERNS.md (tests)

The human owner's name is "you" by default; set LANE_OS_HUMAN=<name> to match your file.
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import subprocess
import sys
from pathlib import Path

DEFAULT_FILE = Path("brain/CONCERNS.md")
PROBE_TIMEOUT = 120
HUMAN = os.environ.get("LANE_OS_HUMAN", "you").strip().lower()

OPEN_HEADING = re.compile(r"^### (?:[^\w\s]\s*)?(\d+)\. (.+)$", re.M)
SECTION_END = re.compile(r"^## ", re.M)
PROBE_LINE = re.compile(r"^\*\*Probe:\*\*\s*`(.+?)`\s*$", re.M)
OWNER_LINE = re.compile(r"^\*\*Owner:\*\*\s*(.+?)\s*$", re.M)
STAMP_LINE = re.compile(r"^\*Probed \d{4}-\d{2}-\d{2}:.*?\*\n?", re.M | re.S)


class Concern:
    def __init__(self, number: str, title: str, body: str, start: int, end: int) -> None:
        self.number = number
        self.title = title
        self.body = body
        self.start = start
        self.end = end
        probe = PROBE_LINE.search(body)
        owner = OWNER_LINE.search(body)
        self.probe = probe.group(1) if probe else None
        self.owner = owner.group(1) if owner else None
        self.result: str | None = None
        self.verdict: str | None = None

    @property
    def declared(self) -> bool:
        return bool(self.probe or self.owner)

    @property
    def owned_by_human(self) -> bool:
        return bool(self.owner) and self.owner.split(".")[0].strip().lower() == HUMAN


def parse(text: str) -> list[Concern]:
    """Return the concerns under '## Right Now' only. Resolved items are not probed."""
    m = re.search(r"^## Right Now\b.*$", text, re.M)
    if not m:
        return []
    start = m.start()
    rest = SECTION_END.search(text, m.end())
    stop = rest.start() if rest else len(text)
    region = text[start:stop]

    out: list[Concern] = []
    marks = list(OPEN_HEADING.finditer(region))
    for i, h in enumerate(marks):
        b_start = h.start()
        b_end = marks[i + 1].start() if i + 1 < len(marks) else len(region)
        out.append(Concern(h.group(1), h.group(2), region[b_start:b_end],
                           start + b_start, start + b_end))
    return out


def run_probe(command: str) -> tuple[str, str]:
    """Run one probe. Returns (verdict, detail). Never raises."""
    try:
        proc = subprocess.run(["bash", "-c", command], capture_output=True, text=True,
                              timeout=PROBE_TIMEOUT)
    except subprocess.TimeoutExpired:
        return "UNKNOWN", f"probe timed out after {PROBE_TIMEOUT}s"
    except Exception as exc:  # noqa: BLE001 - a probe must never break the run
        return "UNKNOWN", f"probe could not run: {exc}"

    lines = (proc.stdout or "").strip().splitlines()
    if not lines:
        err = (proc.stderr or "").strip().splitlines()
        return "UNKNOWN", (err[0][:200] if err else "probe printed nothing")

    first = lines[0].strip()
    head = first.split(None, 1)
    verdict = head[0].upper()
    detail = head[1].strip() if len(head) > 1 else ""
    if verdict not in {"CLOSED", "OPEN", "UNKNOWN"}:
        return "UNKNOWN", f"probe printed an unrecognized verdict: {first[:160]}"
    if proc.returncode != 0 and verdict != "UNKNOWN":
        return "UNKNOWN", f"probe printed {verdict} but exited {proc.returncode}"
    return verdict, detail


def stamp(body: str, today: str, verdict: str, detail: str) -> str:
    """Replace any prior stamp in this concern with the current one."""
    body = STAMP_LINE.sub("", body)
    text = f"*Probed {today}: {verdict}"
    if detail:
        text += f", {detail}"
    text += "*\n"
    return "\n".join(body.rstrip("\n").split("\n")) + "\n\n" + text + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="run probes, write nothing")
    ap.add_argument("--check", action="store_true", help="report undeclared concerns only")
    ap.add_argument("--file", type=Path, default=DEFAULT_FILE)
    args = ap.parse_args()

    if not args.file.exists():
        print(f"{args.file} not found (run from the spine root)", file=sys.stderr)
        return 2

    text = args.file.read_text(encoding="utf-8")
    concerns = parse(text)
    if not concerns:
        print("no open concerns found under '## Right Now'")
        return 0

    undeclared = [c for c in concerns if not c.declared]

    if args.check:
        if undeclared:
            print(f"{len(undeclared)} open concern(s) declare neither a Probe nor an Owner, "
                  "so nothing can ever close them without a human re-reading the file:")
            for c in undeclared:
                print(f"      #{c.number} {c.title[:88]}")
            return 1
        print(f"all {len(concerns)} open concerns declare a Probe or an Owner")
        return 0

    today = dt.date.today().isoformat()
    probed = [c for c in concerns if c.probe]
    owned = [c for c in concerns if c.owner and not c.probe]

    for c in probed:
        c.verdict, c.result = run_probe(c.probe)

    if not args.dry_run:
        # Rewrite from the bottom up so earlier offsets stay valid.
        for c in sorted(probed, key=lambda x: x.start, reverse=True):
            new_body = stamp(c.body, today, c.verdict or "UNKNOWN", c.result or "")
            text = text[: c.start] + new_body + text[c.end:]
        args.file.write_text(text, encoding="utf-8")

    ready = [c for c in probed if c.verdict == "CLOSED"]
    unknown = [c for c in probed if c.verdict == "UNKNOWN"]
    human = [c for c in owned if c.owned_by_human]
    lanes = [c for c in owned if not c.owned_by_human]

    print(f"probed {len(probed)} of {len(concerns)} open concerns ({today})")
    if ready:
        print(f"\nREADY TO CLOSE ({len(ready)}), the closing event has happened; confirm, then move to the archive:")
        for c in ready:
            print(f"  #{c.number} {c.title}\n      {c.result}")
    if unknown:
        print(f"\nCOULD NOT PROBE ({len(unknown)}), recorded, not treated as evidence:")
        for c in unknown:
            print(f"  #{c.number} {c.title[:76]}\n      {c.result}")
    if human:
        print(f"\nDECISIONS OWED ({len(human)}), no probe can close these, only {HUMAN}:")
        for c in human:
            print(f"  #{c.number} {c.title}")
    if lanes:
        print(f"\nOWNED WORK ({len(lanes)}), no passive signal; a lane has to do it:")
        for c in lanes:
            print(f"  #{c.number} [{c.owner.split('.')[0].strip()}] {c.title}")
    if undeclared:
        print(f"\nUNDECLARED ({len(undeclared)}), add a Probe or an Owner:")
        for c in undeclared:
            print(f"  #{c.number} {c.title}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
