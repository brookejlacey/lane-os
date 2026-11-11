#!/usr/bin/env python3
"""Asserts the rules sync never makes a lane load the constitution twice.

install.sh links ~/.claude/CLAUDE.md to the spine's global/CLAUDE.md, so the rules
already load in every Claude session, whatever the working directory, and that copy is
never stale. A lane CLAUDE.md that also imports the synced copy (.claude/global-rules.md)
loads the same rules a second time, and the second copy is always one sync behind. A
hand fix in a lane cannot hold while the sync writes the import back on its next run,
so this asserts the SOURCE:

  * ensure_stub() writes no import into a new stub
  * it removes an import it finds, wherever it sits, and keeps every line of the lane's own
  * a lane file that never had the import is left byte for byte as it was
  * a second sync changes nothing (idempotent)
  * the sync's report warns while a lane still imports the copy, and stops once it is gone
  * a full scratch run of scripts/sync-rules.py leaves no import in the lane it wrote,
    and still writes the generated copy and the AGENTS.md block

Every repo here lives in a temp dir. Nothing touches a real lane.

Run: python3 scripts/tests-no-duplicate-rules-import.py
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# A test that runs git must see only its own scratch repos. Inside a pre-commit hook
# GIT_DIR and GIT_INDEX_FILE point at the live repo, and every git call below would
# land there instead.
for _k in [k for k in os.environ if k.startswith("GIT_")]:
    del os.environ[_k]

HERE = Path(__file__).resolve().parent
SYNC = HERE / "sync-rules.py"
_spec = importlib.util.spec_from_file_location("sync_rules", SYNC)
sync = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(sync)

COPY_REL = ".claude/global-rules.md"
IMPORT = f"@{COPY_REL}"
HEADER = "<!-- GENERATED from the spine by scripts/sync-rules.py. Do not edit here. -->"
FAILS = 0


def warning_for(repo: Path) -> str | None:
    fn = getattr(sync, "stub_warning", None)
    return fn(repo, "CLAUDE.md", COPY_REL) if fn else "the sync has no stub_warning()"


def check(label: str, expected, actual) -> None:
    global FAILS
    ok = expected == actual
    FAILS += 0 if ok else 1
    print(f"  {'ok  ' if ok else 'FAIL'}  {label}" + ("" if ok else f"  (expected {expected!r}, got {actual!r})"))


def stub_case(label: str, before: str | None, keep: tuple[str, ...] = (), unchanged: bool = False) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp) / "example-app"
        repo.mkdir()
        stub = repo / "CLAUDE.md"
        if before is not None:
            stub.write_text(before, encoding="utf-8")
        action = sync.ensure_stub(repo, HEADER, "CLAUDE.md", COPY_REL)
        out = stub.read_text(encoding="utf-8")
        print(f"{label}  ({action})")
        check("no import line is left", False, any(l.strip() == IMPORT for l in out.splitlines()))
        for fragment in keep:
            check(f"lane content kept: {fragment!r}", True, fragment in out)
        if unchanged:
            check("the file is byte for byte as it was", before, out)
        sync.ensure_stub(repo, HEADER, "CLAUDE.md", COPY_REL)
        check("a second sync changes nothing", out, stub.read_text(encoding="utf-8"))
        check("the sync's report no longer warns", None, warning_for(repo))


def full_run() -> None:
    """scripts/sync-rules.py end to end, in a scratch spine and a scratch workspace root."""
    print("a full sync run in a scratch workspace")
    with tempfile.TemporaryDirectory() as tmp:
        t = Path(tmp)
        spine, work = t / "spine", t / "work"
        (spine / "scripts").mkdir(parents=True)
        (spine / "global").mkdir()
        for name in ("sync-rules.py", "workspace_lib.py", "publish-shared-repo.py"):
            shutil.copy(HERE / name, spine / "scripts" / name)
        shutil.copy(HERE.parent / "workspace.toml", spine / "workspace.toml")
        (spine / "global" / "CLAUDE.md").write_text("# Rules\n\nThe scratch constitution.\n", encoding="utf-8")
        subprocess.run(["git", "init", "-q", str(spine)], check=True)

        lane = work / "example-app"
        lane.mkdir(parents=True)
        subprocess.run(["git", "init", "-q", str(lane)], check=True)
        hooks = t / "no-hooks"
        hooks.mkdir()
        for key, val in (("user.email", "test@example.invalid"), ("user.name", "test"),
                         ("commit.gpgsign", "false"), ("core.hooksPath", str(hooks))):
            subprocess.run(["git", "-C", str(lane), "config", key, val], check=True)
        # A lane bootstrapped by an older sync: generated copy, import on line 1, own notes.
        (lane / ".claude").mkdir()
        (lane / ".claude" / "global-rules.md").write_text(HEADER + "\n\nold rules\n", encoding="utf-8")
        (lane / "CLAUDE.md").write_text(f"{IMPORT}\n\n# example-app\n\nRun the tests with make test.\n",
                                        encoding="utf-8")

        env = dict(os.environ, LANE_OS_ROOT=str(spine), LANE_OS_WORKSPACE_ROOTS=str(work), HOME=str(t))
        dry = subprocess.run([sys.executable, str(spine / "scripts" / "sync-rules.py"), "--dry-run", "--json"],
                             capture_output=True, text=True, env=env)
        rows = json.loads(dry.stdout or "{}").get("sync_rules", []) if dry.returncode == 0 else []
        row = rows[0] if rows else {}
        check("a dry run reports the lane", "example-app", row.get("repo"))
        check("...and warns that its CLAUDE.md loads the rules a second time", True,
              "loads the rules a second time" in (row.get("warn") or ""))
        check("...and writes nothing", True, (lane / "CLAUDE.md").read_text(encoding="utf-8").startswith(IMPORT))

        real = subprocess.run([sys.executable, str(spine / "scripts" / "sync-rules.py"), "--no-push", "--json"],
                              capture_output=True, text=True, env=env)
        check("the real run exits 0", 0, real.returncode)
        rows = json.loads(real.stdout or "{}").get("sync_rules", []) if real.returncode == 0 else []
        row = rows[0] if rows else {}
        out = (lane / "CLAUDE.md").read_text(encoding="utf-8")
        check("the lane CLAUDE.md no longer imports the rules", False, IMPORT in out)
        check("...and keeps the lane's own notes", True, "Run the tests with make test." in out)
        check("...and the report stops warning", None, row.get("warn"))
        copy = (lane / COPY_REL).read_text(encoding="utf-8")
        check("the generated copy is still written, and current", True, "The scratch constitution." in copy)
        agents = lane / "AGENTS.md"
        check("the AGENTS.md block is still written", True,
              agents.is_file() and "The scratch constitution." in agents.read_text(encoding="utf-8"))
        committed = subprocess.run(["git", "-C", str(lane), "show", "HEAD:CLAUDE.md"],
                                   capture_output=True, text=True).stdout
        check("the committed CLAUDE.md carries no import either", False, IMPORT in committed or not committed)


def main() -> int:
    stub_case("no CLAUDE.md yet", None)
    stub_case("a stub an older sync created, import under the heading",
              f"{HEADER}\n\n# example-app\n\n{IMPORT}\n\nMechanism only below this line.\n",
              keep=(HEADER, "# example-app", "Mechanism only below this line."))
    stub_case("a hand-written lane file, import on line 1",
              f"{IMPORT}\n\n# example-app\n\nthe lane's own mechanism\n",
              keep=("# example-app", "the lane's own mechanism"))
    stub_case("a hand-written lane file, import at the bottom",
              f"# example-app\n\nthe lane's own mechanism\n\n{IMPORT}\n",
              keep=("# example-app", "the lane's own mechanism"))
    stub_case("the import twice",
              f"{IMPORT}\n\n# example-app\n\n{IMPORT}\n\nthe lane's own mechanism\n",
              keep=("# example-app", "the lane's own mechanism"))
    stub_case("a hand-written lane file that never had the import",
              "# example-app\n\nthe lane's own mechanism\n",
              keep=("# example-app", "the lane's own mechanism"), unchanged=True)

    print("the report warns while the import is present")
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        (repo / "CLAUDE.md").write_text(f"# example-app\n\n{IMPORT}\n", encoding="utf-8")
        warning = warning_for(repo) or ""
        check("an import line is a warning", True, "loads the rules a second time" in warning)
        (repo / "CLAUDE.md").write_text(f"# example-app\n\nSee {IMPORT} for the rules.\n", encoding="utf-8")
        check("an inline mention is a warning too (it imports just the same)", True,
              bool(warning_for(repo)))
        (repo / "CLAUDE.md").write_text("# example-app\n", encoding="utf-8")
        check("a lane file without it is not", None, warning_for(repo))

    full_run()

    print(f"tests-no-duplicate-rules-import: {'PASS' if FAILS == 0 else f'FAIL ({FAILS})'}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    raise SystemExit(main())
