#!/usr/bin/env python3
"""Enumerate the decay surface: every standing rule that no machine enforces.

THE HONEST LIMIT, STATED FIRST
------------------------------
You cannot automatically detect that an ungated rule has been broken. That is what
"ungated" means. A detector for a specific rule IS a gate, and if you can write one you
should just write it. So this script does not hunt for violations. It does the one thing
that IS mechanical: it lists exactly where a rule can die quietly, so the list can be
worked down instead of rediscovered one miss at a time.

Every rule bullet in `global/CLAUDE.md` is in one of three states:

  GATED       names a `Hook:` or a `Check N`. Cannot be forgotten.
  JUDGMENT    triaged in global/rule-triage.tsv as having no deterministic signature,
              with the reason recorded. Not a gap. Stops showing up as one.
  UNTRIAGED   nobody has decided which of the above it is. THIS is the decay surface,
              and it is the work queue.

The ratchet: `audit-cheap.sh` Check 12 requires the preamble line
`Coverage today: N of M bullets are gated.` to match what this script measures, so the
number is always read from the file and never hand-typed. Restating it downward means
naming which gate was removed and why.

WHY THIS EXISTS
---------------
Rules held only in prose decay, and only those do. Measured across the four files loaded
into every session of the spine this was built in: the two with a byte budget were flat
or smaller after four months; the two governed only by a written brevity rule had grown
2x and 5.2x. Both were found by a human noticing. That is the thing being fixed.

USAGE
-----
  scripts/find-decayed-rules.py              the full triage report
  scripts/find-decayed-rules.py --untriaged  just the work queue
  scripts/find-decayed-rules.py --count      "gated judgment untriaged", for the check
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

RULES = Path("global/CLAUDE.md")
TRIAGE = Path("global/rule-triage.tsv")
# A rule is gated if it names its enforcement in ANY of the forms the rules file uses.
# Under-counting the gates overstates the decay surface, which is its own quiet failure.
GATED = re.compile(
    r"Hook:|Hook `|Guard:|Same hook|Check(?:s)? \d|Enforced in `|scripts/hooks/[a-z-]+\.py"
)
# The first bolded phrase, else the first clause, is stable enough to key a rule on.
KEY = re.compile(r"\*\*(.+?)\*\*|^- ([^.:;]{6,60})")


def rule_key(bullet: str) -> str:
    m = KEY.search(bullet)
    raw = (m.group(1) or m.group(2)) if m else bullet[2:62]
    return re.sub(r"[^a-z0-9]+", "-", raw.lower()).strip("-")[:60]


def load_triage() -> dict[str, str]:
    out: dict[str, str] = {}
    if not TRIAGE.exists():
        return out
    for line in TRIAGE.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) >= 2:
            out[parts[0].strip()] = parts[1].strip()
    return out


def classify(text: str, triage: dict[str, str]):
    gated: list[str] = []
    judgment: list[tuple[str, str]] = []
    untriaged: list[tuple[str, str]] = []
    for line in text.split("\n"):
        if not line.startswith("- "):
            continue
        key = rule_key(line)
        if GATED.search(line):
            gated.append(line)
        elif key in triage:
            judgment.append((key, line))
        else:
            untriaged.append((key, line))
    return gated, judgment, untriaged


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--untriaged", action="store_true")
    ap.add_argument("--count", action="store_true")
    args = ap.parse_args()

    if not RULES.exists():
        print(f"{RULES} not found (run from the spine root)", file=sys.stderr)
        return 2

    gated, judgment, untriaged = classify(RULES.read_text(encoding="utf-8"), load_triage())

    if args.count:
        print(f"{len(gated)} {len(judgment)} {len(untriaged)}")
        return 0

    def show(line: str) -> str:
        text = re.sub(r"\s+", " ", line[2:]).strip()
        return text[:150] + ("..." if len(text) > 150 else "")

    if args.untriaged:
        if not untriaged:
            print("no untriaged rules: every rule is gated or recorded as judgment")
            return 0
        print(f"{len(untriaged)} rule(s) on the decay surface: gate them or triage them:\n")
        for key, line in untriaged:
            print(f"  [{key}]\n    {show(line)}\n")
        return 0

    total = len(gated) + len(judgment) + len(untriaged)
    print(f"{total} standing rules\n")
    print(f"  GATED      {len(gated):>3}   a hook or a check enforces it")
    print(f"  JUDGMENT   {len(judgment):>3}   triaged: no deterministic signature exists")
    print(f"  UNTRIAGED  {len(untriaged):>3}   the decay surface, and the work queue")
    if untriaged:
        print("\nUNTRIAGED: for each, either build the gate or record why none can exist:\n")
        for key, line in untriaged:
            print(f"  [{key}]\n    {show(line)}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
