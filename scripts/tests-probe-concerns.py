#!/usr/bin/env python3
"""Asserts probe-concerns.py flags what it should and never closes on its own.

A checker that only ever prints "all declared" is indistinguishable from a broken one,
so this plants each shape of concern in a scratch file and asserts the verdicts:
an undeclared item fails --check; a CLOSED probe is flagged READY but the item stays;
a failing probe is UNKNOWN, never OPEN; an Owner of "you" is a decision owed and any
other Owner is lane work.

Run: python3 scripts/tests-probe-concerns.py
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "probe-concerns.py"
FAILS = 0


def check(label: str, expected, actual) -> None:
    global FAILS
    ok = expected == actual
    FAILS += 0 if ok else 1
    print(f"  {'ok  ' if ok else 'FAIL'}  {label}" + ("" if ok else f"  (expected {expected!r}, got {actual!r})"))


def run(path: Path, *args: str) -> tuple[int, str]:
    env = dict(os.environ, LANE_OS_HUMAN="you")
    p = subprocess.run([sys.executable, str(SCRIPT), "--file", str(path), *args],
                       capture_output=True, text=True, env=env)
    return p.returncode, p.stdout + p.stderr


BODY = """# Concerns

## Right Now

### 🟡 1. A probe that reports closed
**Probe:** `echo "CLOSED the event happened"`

### 🔴 2. A probe that reports open
**Probe:** `echo "OPEN still waiting"`

### 🟡 3. A probe that cannot run
**Probe:** `exit 3`

### 🟡 4. A probe that prints closed but exits nonzero
**Probe:** `echo CLOSED; exit 1`

### 🟡 5. A decision owed
**Owner:** you

### 🟡 6. Work a lane owns
**Owner:** the alpha lane

## Resolved

### 🟡 7. An old one in the resolved section, undeclared on purpose
nothing here
"""

UNDECLARED = BODY.replace("**Owner:** the alpha lane\n", "")


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        f = Path(tmp) / "CONCERNS.md"

        print("--check")
        f.write_text(BODY, encoding="utf-8")
        rc, out = run(f, "--check")
        check("every declared item passes --check", 0, rc)
        check("...and resolved items are not parsed", False, "#7" in out)
        f.write_text(UNDECLARED, encoding="utf-8")
        rc, out = run(f, "--check")
        check("an undeclared item fails --check", 1, rc)
        check("...and is named", True, "#6" in out)

        print("a real run")
        f.write_text(BODY, encoding="utf-8")
        rc, out = run(f)
        check("the run exits 0", 0, rc)
        check("a CLOSED probe is flagged READY TO CLOSE", True, "READY TO CLOSE (1)" in out and "#1" in out)
        check("a failing probe is UNKNOWN, not OPEN", True, "COULD NOT PROBE (2)" in out)
        check("CLOSED with a nonzero exit is UNKNOWN", True, "#4" in out.split("COULD NOT PROBE")[1].split("DECISIONS")[0])
        check("Owner: you is a decision owed", True, "DECISIONS OWED (1)" in out and "#5" in out)
        check("any other Owner is lane work", True, "OWNED WORK (1)" in out and "#6" in out)
        after = f.read_text(encoding="utf-8")
        check("the CLOSED item is still in the file (a probe never closes)", True, "### 🟡 1." in after)
        check("probed items carry a dated stamp", 4, after.count("*Probed "))

        print("stamps replace, never accumulate")
        rc, _ = run(f)
        check("a second run keeps one stamp per item", 4, f.read_text(encoding="utf-8").count("*Probed "))

        print("--dry-run")
        f.write_text(BODY, encoding="utf-8")
        run(f, "--dry-run")
        check("dry-run writes nothing", BODY, f.read_text(encoding="utf-8"))

    print(f"tests-probe-concerns: {'PASS' if FAILS == 0 else f'FAIL ({FAILS})'}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    raise SystemExit(main())
