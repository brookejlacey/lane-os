#!/usr/bin/env python3
"""Asserts the publisher refuses to publish from a spine checkout that is behind origin.

Every file the publisher writes is derived from the spine, and the shared repo is reset to
its origin and overwritten wholesale. A checkout that is behind does not publish less; it
publishes OLD, silently reverting what a current checkout published before it. The reader
then acts on a superseded document. So the publisher fetches its own branch first and
refuses (exit 3, nothing written) when HEAD..origin is non-empty, and refuses when it
cannot fetch, because "cannot know" must not read as "fine".

Each case runs scripts/publish-shared-repo.py end to end, in a scratch spine cloned from
a scratch origin, against a scratch shared repo with its own scratch origin:

  * level with origin publishes, and the push lands (the gate does not block the good case)
  * ahead of origin publishes (local work not pushed yet is still newer)
  * two commits behind REFUSES with exit 3, and the shared repo is untouched
  * behind and ahead at once REFUSES
  * an unreachable origin REFUSES (fails closed)
  * a detached HEAD REFUSES
  * --dry-run from behind writes nothing and says why

Run: python3 scripts/tests-publish-stale-gate.py
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# Run from the pre-commit gate, this inherits GIT_INDEX_FILE (and GIT_DIR in a linked
# worktree) pointing at the live repo. Every git call here must see only scratch repos.
for _k in [k for k in os.environ if k.startswith("GIT_")]:
    del os.environ[_k]

HERE = Path(__file__).resolve().parent
AUDIENCE = "example-partner-docs"
FAILS = 0


def check(label: str, expected, actual) -> None:
    global FAILS
    ok = expected == actual
    FAILS += 0 if ok else 1
    print(f"  {'ok  ' if ok else 'FAIL'}  {label}" + ("" if ok else f"  (expected {expected!r}, got {actual!r})"))


def git(cwd: Path, *args: str) -> str:
    done = subprocess.run(["git", "-c", "user.name=test", "-c", "user.email=test@example.invalid",
                           "-c", "commit.gpgsign=false", *args], cwd=cwd, capture_output=True, text=True)
    if done.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} in {cwd}: {done.stderr.strip()}")
    return done.stdout.strip()


def commit(repo: Path, name: str, text: str | None = None) -> None:
    path = repo / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text if text is not None else name + "\n", encoding="utf-8")
    git(repo, "add", name)
    git(repo, "commit", "-q", "-m", name)


class World:
    """A spine origin and its clone, and a shared repo with its own origin."""

    def __init__(self, tmp: Path) -> None:
        self.tmp = tmp
        self.origin = tmp / "spine-origin"
        self.origin.mkdir()
        git(self.origin, "init", "-q", "-b", "main")
        (self.origin / "scripts" / "hooks").mkdir(parents=True)
        for name in ("publish-shared-repo.py", "workspace_lib.py"):
            shutil.copy(HERE / name, self.origin / "scripts" / name)
        shutil.copy(HERE / "hooks" / "shared-repo-pre-commit.sh", self.origin / "scripts" / "hooks")
        shutil.copy(HERE.parent / "workspace.toml", self.origin / "workspace.toml")
        commit(self.origin, "projects/example-app/docs/overview.md", "# Overview\n\nThe current version.\n")
        git(self.origin, "add", "-A")
        git(self.origin, "commit", "-q", "-m", "the spine")
        self.spine = tmp / "spine"
        git(tmp, "clone", "-q", str(self.origin), str(self.spine))

        self.target_origin = tmp / "shared-origin.git"
        git(tmp, "init", "-q", "--bare", "-b", "main", str(self.target_origin))
        self.target = tmp / AUDIENCE
        git(tmp, "clone", "-q", str(self.target_origin), str(self.target))
        git(self.target, "checkout", "-q", "-B", "main")
        commit(self.target, ".gitignore", "")
        git(self.target, "push", "-q", "-u", "origin", "main")
        for key, val in (("user.name", "test"), ("user.email", "test@example.invalid"), ("commit.gpgsign", "false")):
            git(self.target, "config", key, val)

    def publish(self, *extra: str) -> subprocess.CompletedProcess:
        env = dict(os.environ, LANE_OS_ROOT=str(self.spine), LANE_OS_SHARED_TARGET=str(self.target),
                   LANE_OS_WORKSPACE_ROOTS=str(self.tmp / "no-roots"), HOME=str(self.tmp))
        return subprocess.run([sys.executable, str(self.spine / "scripts" / "publish-shared-repo.py"),
                               AUDIENCE, *extra], capture_output=True, text=True, env=env)

    def target_state(self) -> tuple:
        files = sorted(p.relative_to(self.target).as_posix() for p in self.target.rglob("*")
                       if p.is_file() and ".git" not in p.relative_to(self.target).parts)
        hook = (self.target / ".git" / "hooks" / "pre-commit").is_file()
        return (git(self.target, "rev-parse", "HEAD"), git(self.target_origin, "rev-parse", "main"), files, hook)


def case(label: str, mutate, *, refused: bool, why: str = "", dry_run: bool = False) -> None:
    print(label)
    with tempfile.TemporaryDirectory() as raw:
        w = World(Path(raw))
        mutate(w)
        before = w.target_state()
        p = w.publish(*(["--dry-run"] if dry_run else []))
        after = w.target_state()
        if dry_run:
            check("a dry run exits 0", 0, p.returncode)
            # [:3]: commit, push and files. A dry run still keeps the shared repo's own
            # pre-commit lock installed, which is ensure_repo_hook's job, not this gate's.
            check("...commits, pushes and writes nothing", before[:3], after[:3])
            check(f"...and says why a real run would refuse ({why!r})", True, why in p.stderr)
        elif refused:
            check("the publish is refused with exit 3", 3, p.returncode)
            check(f"...naming the reason ({why!r})", True, why in p.stderr)
            check("...and the shared repo is untouched (no commit, no push, no file, no hook)", before, after)
        else:
            check("the publish succeeds", 0, p.returncode)
            check("...and the push landed on the shared repo's origin", True, after[1] != before[1])
            published = (w.target / "overview.md").read_text(encoding="utf-8") if (w.target / "overview.md").is_file() else ""
            check("...with the spine's current text", True, "The current version." in published)


def behind(w: World) -> None:
    commit(w.origin, "projects/example-app/docs/overview.md", "# Overview\n\nA newer version.\n")
    commit(w.origin, "projects/example-app/docs/second.md", "# Second\n")


def ahead(w: World) -> None:
    commit(w.spine, "projects/example-app/docs/local.md", "# Local, not pushed yet\n")


def main() -> int:
    case("level with origin", lambda w: None, refused=False)
    case("ahead of origin, not behind", ahead, refused=False)
    case("two commits behind origin", behind, refused=True, why="2 commit(s) behind")
    case("behind and ahead at once", lambda w: (behind(w), ahead(w)), refused=True, why="behind")
    case("origin unreachable",
         lambda w: git(w.spine, "remote", "set-url", "origin", str(w.tmp / "no-such-repo")),
         refused=True, why="could not fetch")
    case("detached HEAD", lambda w: git(w.spine, "checkout", "-q", "--detach", "HEAD"),
         refused=True, why="not on a branch")
    case("--dry-run from behind", behind, refused=True, why="behind", dry_run=True)

    print(f"tests-publish-stale-gate: {'PASS' if FAILS == 0 else f'FAIL ({FAILS})'}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    raise SystemExit(main())
