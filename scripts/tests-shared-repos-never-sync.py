#!/usr/bin/env python3
"""Asserts the constitution can never sync into a repo an outside reader sees.

The deny list is derived from the publisher's AUDIENCES table by a static parse. A
rename inside publish-shared-repo.py would make that parse return an empty set, which
denies nothing extra and reads as a pass everywhere else. So this asserts, in a scratch
workspace root:

  * the parse still finds the audiences (an empty result is the dangerous failure)
  * every audience is denied, and the hand-kept list still works alongside
  * a repo named after an audience that carries a generated copy is NOT a sync target
  * an ordinary repo with a generated copy IS (a deny list that denies everything passes
    the other assertions and stops the sync working at all)
  * the publisher's own scrub aborts on a planted hit and passes a clean tree

Run: python3 scripts/tests-shared-repos-never-sync.py
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import workspace_lib as wl  # noqa: E402

FAILS = 0


def check(label: str, expected, actual) -> None:
    global FAILS
    ok = expected == actual
    FAILS += 0 if ok else 1
    print(f"  {'ok  ' if ok else 'FAIL'}  {label}" + ("" if ok else f"  (expected {expected!r}, got {actual!r})"))


def main() -> int:
    manifest = wl.load_manifest()
    audiences = wl.published_audience_names()
    check("the publisher's audience table is still readable", True, len(audiences) >= 1)
    check("...and names the example audience", True, "example-partner-docs" in audiences)

    denied = wl.deny_sync_names(manifest)
    for name in sorted(audiences):
        check(f"{name} is denied the rules sync", True, name in denied)
    for name in manifest["globals"].get("deny_sync", []):
        check(f"{name} (hand-listed) is still denied", True, name in denied)
    check("the spine itself is denied", True, wl.spine_root().name in denied)

    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "work"
        copy_rel = manifest["globals"]["sync_copy"]
        header = manifest["globals"]["generated_header"]
        for name in ("ordinary-app", "example-partner-docs"):
            repo = work / name
            (repo / ".git").mkdir(parents=True)
            (repo / copy_rel).parent.mkdir(parents=True, exist_ok=True)
            (repo / copy_rel).write_text(header + "\n\nrules\n", encoding="utf-8")
        os.environ["LANE_OS_WORKSPACE_ROOTS"] = str(work)
        targets = {r.name for r in wl.sync_target_repos(manifest)}
        check("an ordinary repo with a generated copy is a sync target", True, "ordinary-app" in targets)
        check("the shared repo with the SAME generated copy is not", False, "example-partner-docs" in targets)

        # The publisher's scrub, on a scratch lane.
        spine = Path(tmp) / "spine"
        lane = spine / "projects" / "example-app" / "docs"
        lane.mkdir(parents=True)
        (spine / ".git").mkdir()
        (spine / "workspace.toml").write_text((wl.spine_root() / "workspace.toml").read_text())
        (spine / "scripts").mkdir()
        for f in ("publish-shared-repo.py", "workspace_lib.py"):
            (spine / "scripts" / f).write_text((HERE / f).read_text())
        (spine / "scripts" / "hooks").mkdir()
        (spine / "scripts" / "hooks" / "shared-repo-pre-commit.sh").write_text("#!/bin/sh\nexit 0\n")
        (lane / "overview.md").write_text("# Overview\n\nAll good here.\n")
        env = dict(os.environ, LANE_OS_ROOT=str(spine), LANE_OS_SHARED_TARGET=str(Path(tmp) / "nowhere"))
        cmd = [sys.executable, str(spine / "scripts" / "publish-shared-repo.py"), "example-partner-docs", "--dry-run"]
        p = subprocess.run(cmd, capture_output=True, text=True, env=env)
        check("a clean lane passes the publisher's dry run", 0, p.returncode)
        check("...and lists what it would publish", True, "would publish  overview.md" in p.stdout)
        (lane / "notes.md").write_text("Token: ghp_" + "B" * 36 + "\n")
        p = subprocess.run(cmd, capture_output=True, text=True, env=env)
        check("a planted credential aborts the publish", 2, p.returncode)
        check("...naming the file and the reason", True, "notes.md" in p.stderr and "a credential" in p.stderr)
        (lane / "notes.md").write_text("Fine. INTERNAL ONLY: the walk-away price is 40.\n")
        p = subprocess.run(cmd, capture_output=True, text=True, env=env)
        check("an internal marker aborts too", 2, p.returncode)

    print(f"tests-shared-repos-never-sync: {'PASS' if FAILS == 0 else f'FAIL ({FAILS})'}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    raise SystemExit(main())
