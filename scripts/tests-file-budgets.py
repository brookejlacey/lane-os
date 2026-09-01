#!/usr/bin/env python3
"""Asserts that the state-file budget gate BLOCKS, and blocks at the right level.

A size check that only ever prints "all clear" is indistinguishable from one that is
silently broken. These cases were mutation-checked against a gate with its comparisons
removed, which they fail on every assertion.

Run: python3 scripts/tests-file-budgets.py
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "check-file-budgets.py"
FAILS = 0


def check(label: str, expected, actual) -> None:
    global FAILS
    ok = expected == actual
    FAILS += 0 if ok else 1
    print(f"  {'ok  ' if ok else 'FAIL'}  {label}" + ("" if ok else f"  (expected {expected!r}, got {actual!r})"))


def run(root: Path, *args: str, roots: str = "/nonexistent") -> tuple[int, str]:
    env = dict(os.environ, LANE_OS_BUDGET_ROOT=str(root), LANE_OS_WORKSPACE_ROOTS=roots)
    proc = subprocess.run([sys.executable, str(SCRIPT), *args], env=env, capture_output=True, text=True)
    return proc.returncode, proc.stdout + proc.stderr


def write(path: Path, chars: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("x" * chars, encoding="utf-8")


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "spine"

        print("clean tree")
        write(root / "brain" / "ACTIVE_NOW.md", 1_000)
        write(root / "projects" / "alpha" / "MEMORY.md", 1_000)
        rc, out = run(root, "--over-only")
        check("a tree inside every budget exits 0", 0, rc)
        check("...and says so", True, "inside its budget" in out)

        print("warn level")
        write(root / "projects" / "alpha" / "MEMORY.md", 32_001)
        rc, out = run(root, "--over-only")
        check("a warn-level file exits 1", 1, rc)
        check("...and names the file", True, "projects/alpha/MEMORY.md" in out)
        check("...and does not escalate to a ceiling breach", False, "OVER CEILING" in out)

        print("hard ceiling")
        write(root / "brain" / "ACTIVE_NOW.md", 24_001)
        rc, out = run(root, "--over-only")
        check("a file over its hard ceiling exits 2", 2, rc)
        check("...and marks it as a ceiling breach", True, "OVER CEILING" in out)

        print("exactly at the threshold is not over")
        write(root / "brain" / "ACTIVE_NOW.md", 14_000)
        write(root / "projects" / "alpha" / "MEMORY.md", 32_000)
        rc, _ = run(root, "--over-only")
        check("a file exactly at its budget exits 0", 0, rc)

        print("aggregate of the always-loaded four")
        write(root / "global" / "CLAUDE.md", 23_500)  # 23.5k+19k+14k+22k = 78,500
        write(root / "memory" / "MEMORY.md", 19_000)
        write(root / "brain" / "ACTIVE_NOW.md", 14_000)
        write(root / "brain" / "CONCERNS.md", 22_000)
        rc, out = run(root, "--over-only")
        check("the aggregate fires when every file passes alone", 1, rc)
        check("...and names the sum, not one file", True, "always-loaded" in out)

        print("projects/ alias symlinks are not double counted")
        for f in ("global/CLAUDE.md", "memory/MEMORY.md", "brain/ACTIVE_NOW.md", "brain/CONCERNS.md"):
            write(root / f, 100)
        write(root / "projects" / "alpha" / "MEMORY.md", 32_001)
        (root / "projects" / "alpha-alias").symlink_to(root / "projects" / "alpha")
        rc, out = run(root, "--over-only")
        check("the alias exits 1, same as the real lane", 1, rc)
        check("...reporting the canonical path", True, "projects/alpha/MEMORY.md" in out)
        check("...and NOT the alias", False, "alpha-alias" in out)
        write(root / "projects" / "alpha" / "MEMORY.md", 100)

        print("templates are not budgeted")
        write(root / "projects" / "_TEMPLATE" / "STATUS.md", 40_000)
        rc, _ = run(root, "--over-only")
        check("a _TEMPLATE file is ignored", 0, rc)

        print("code-repo standard")
        work = Path(tmp) / "work"
        repo = work / "alpha"
        (repo / ".git").mkdir(parents=True)
        (repo / "DECISIONS.md").write_text("head\n" * 10 + "\n## Archive\n" + "tail\n" * 5000)
        (repo / "CLAUDE.md").write_text("x" * 25_001)
        rc, out = run(root, "--over-only", roots=str(work))
        check("an oversized code-repo CLAUDE.md warns", 1, rc)
        check("...naming the repo file", True, "work/alpha/CLAUDE.md" in out)
        check("DECISIONS.md is charged only above ## Archive", False, "DECISIONS.md" in out)

        spec = importlib.util.spec_from_file_location("budgets", SCRIPT)
        budgets = importlib.util.module_from_spec(spec); spec.loader.exec_module(budgets)
        check("read_first_size stops at the divider", True, budgets.read_first_size(repo / "DECISIONS.md") < 200)
        check("AGENTS.md is deliberately not in the code-repo table", False,
              any(n == "AGENTS.md" for n, _, _ in budgets.CODE_REPO_BUDGETS))

    print(f"tests-file-budgets: {'PASS' if FAILS == 0 else f'FAIL ({FAILS})'}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    raise SystemExit(main())
