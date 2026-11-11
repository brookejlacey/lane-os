#!/usr/bin/env python3
"""Propagate the constitution into every code lane, safely.

WHAT IT WRITES, per target repo (paths from workspace.toml):
  .claude/global-rules.md   a generated copy of global/CLAUDE.md, with a header saying so
  CLAUDE.md                 created if absent, holding the lane's own notes only. It never
                            imports the copy above, and an import line it finds is removed
                            (see ensure_stub); every other line of the lane's file stays
  AGENTS.md                 a marked block holding the same rules, for agents that read it

The rules reach a Claude session through ~/.claude/CLAUDE.md, which install.sh links to
global/CLAUDE.md, so a lane CLAUDE.md that also imported the copy loaded them twice, one
copy a sync behind. The report warns on any lane that still carries the import.

TWO SAFETY PROPERTIES, both of which failed as prose rules before they were code:

1. IT NEVER TOUCHES THE GIT INDEX OF A REPO WITH A SESSION OPEN. It still WRITES the
   files (they are generated, never hand-edited in a lane, and the lane's next commit
   carries them), and defers only `git add` / `git commit`, reporting
   `deferred: session open`. Skipping the repo outright is not a deferral; a lane with a
   long-lived session then never syncs and works to rules the rest of the workspace has
   replaced. Liveness is PID-checked, not guessed (workspace_lib.live_session_cwds).

2. IT NEVER WRITES INTO A REPO PUBLISHED TO AN OUTSIDE READER. The deny list is the
   union of `deny_sync` in workspace.toml and the AUDIENCES of
   scripts/publish-shared-repo.py, parsed from that file. A shared repo is denied the day
   it is created. scripts/tests-shared-repos-never-sync.py asserts the link, and
   audit-cheap Check 13 runs it on every commit.

USAGE
  scripts/sync-rules.py                 write, commit and push in every target
  scripts/sync-rules.py --dry-run       report what would change, write nothing
  scripts/sync-rules.py --no-push       write and commit, do not push
  scripts/sync-rules.py alpha beta      only these repos (an operator override that
                                        bypasses the live-session deferral, never the deny list)
  scripts/sync-rules.py --json          machine-readable rows
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import workspace_lib as wl  # noqa: E402

PUSH_RETRY_ROUNDS = 3


# A lane CLAUDE.md does NOT import the synced copy. ~/.claude/CLAUDE.md is a symlink to
# the spine's global/CLAUDE.md (install.sh makes it), so the rules already load in every
# Claude session whatever the working directory, and that copy is never stale. Importing
# .claude/global-rules.md as well loaded the same rules a second time on every session
# start, the second copy always one sync behind. This function used to write that import,
# so a hand fix in a lane could not hold: the next sync wrote the line back. The copy itself
# stays on disk, because AGENTS.md readers and sync_target_repos() still use it.
NO_IMPORT_NOTICE = (
    "<!-- The constitution loads from ~/.claude/CLAUDE.md (a symlink to the spine's\n"
    "     global/CLAUDE.md) in every Claude session. Do not import the synced copy in\n"
    "     .claude/ from this file: that loads the same rules twice, one copy a sync behind. -->"
)
NOTICE_MARK = NO_IMPORT_NOTICE.splitlines()[0]


def stub_warning(repo: Path, stub_rel: str, copy_rel: str) -> str | None:
    """The report's warning for a lane CLAUDE.md that still loads the rules a second time.

    Any mention counts, not only a line of its own: Claude Code follows an @path written
    inline in prose too. ensure_stub() removes a whole import line; an inline one is for
    a person to reword, so it stays a warning until they do."""
    stub = repo / stub_rel
    if not stub.is_file():
        return None
    if f"@{copy_rel}" in stub.read_text(encoding="utf-8", errors="replace"):
        return f"{stub_rel} imports {copy_rel}, which loads the rules a second time"
    return None


def ensure_stub(repo: Path, header: str, stub_rel: str, copy_rel: str) -> str:
    stub = repo / stub_rel
    import_line = f"@{copy_rel}"
    if not stub.exists():
        stub.write_text(f"{header}\n\n# {repo.name}\n\n{NO_IMPORT_NOTICE}\n\n"
                        "Mechanism only below this line: commands, gotchas, hard rules for this repo. "
                        "Release state lives in the spine's projects/<name>/STATUS.md.\n", encoding="utf-8")
        return "stub created"
    text = stub.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines(keepends=True)
    hits = [i for i, line in enumerate(lines) if line.strip() == import_line]
    if not hits:
        # A lane file that never had the import is the lane's own; leave it byte for byte.
        return "stub current"
    # The first import line becomes the notice, in place, so the lane's heading and line
    # order stay as they were; any further import line goes. A blank line left doubled by
    # a removal goes with it.
    notice_present = NOTICE_MARK in text
    out: list[str] = []
    for i, line in enumerate(lines):
        if i in hits:
            if i == hits[0] and not notice_present:
                out.append(NO_IMPORT_NOTICE + ("\n" if line.endswith("\n") else ""))
            elif out and not out[-1].strip() and i + 1 < len(lines) and not lines[i + 1].strip():
                out.pop()
            continue
        out.append(line)
    while out and not out[0].strip():
        out.pop(0)
    stub.write_text("".join(out), encoding="utf-8")
    where = ", ".join(str(i + 1) for i in hits)
    return f"duplicate rules import removed (line{'s' if len(hits) > 1 else ''} {where})"


def ensure_agents(repo: Path, agents_rel: str, block: str, begin: str, end: str) -> str:
    path = repo / agents_rel
    if not path.exists():
        path.write_text(block, encoding="utf-8")
        return "agents created"
    text = path.read_text(encoding="utf-8", errors="replace")
    existing = wl.marked_block(text, begin, end)
    if existing is None:
        path.write_text(text.rstrip() + "\n\n" + block, encoding="utf-8")
        return "agents block appended"
    if existing.strip() == block.strip():
        return "agents current"
    path.write_text(text.replace(existing, block.strip()), encoding="utf-8")
    return "agents block updated"


def push_with_recovery(repo: Path) -> str:
    """Rebase onto the remote and push again after a rejected push. The commits at stake
    are generated rule state, so a rebase is safe; a CONFLICT is not, and aborts."""
    last = ""
    for attempt in range(1, PUSH_RETRY_ROUNDS + 1):
        rebase = subprocess.run(["git", "-c", "rebase.autoStash=true", "pull", "--rebase", "-q"],
                                cwd=repo, capture_output=True, text=True)
        if rebase.returncode != 0:
            subprocess.run(["git", "rebase", "--abort"], cwd=repo, capture_output=True)
            return f"committed; rebase failed: {rebase.stderr.strip()[:120]}"
        push = subprocess.run(["git", "push", "-q"], cwd=repo, capture_output=True, text=True)
        if push.returncode == 0:
            return "committed + pushed after rebase" if attempt == 1 else f"committed + pushed after {attempt} rebases"
        last = push.stderr.strip()
    return f"committed; push rejected {PUSH_RETRY_ROUNDS}x after rebase: {last[:120]}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("repos", nargs="*")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-push", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    manifest = wl.load_manifest()
    g = manifest["globals"]
    targets = {r.name: r for r in wl.sync_target_repos(manifest)}
    if args.repos:
        deny = wl.deny_sync_names(manifest)
        selected, missing = {}, []
        for name in args.repos:
            found = targets.get(name) or wl.find_repo(name, manifest)
            if found and name not in deny:
                selected[name] = found
            else:
                missing.append(name)
        if missing:
            print(f"no sync target matched (unknown, or denied): {', '.join(missing)}", file=sys.stderr)
            return 1
        targets = selected

    expected = wl.expected_global_rules_text(manifest)
    block = wl.expected_agents_block(manifest)
    header = wl.generated_header(manifest)
    copy_rel, stub_rel, agents_rel = g["sync_copy"], g["stub"], g.get("agents", "AGENTS.md")
    spine = wl.spine_root()
    sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=spine, capture_output=True,
                         text=True).stdout.strip() or "unknown"
    live = set() if args.repos else wl.live_session_cwds()

    rows = []
    for repo in sorted(targets.values(), key=lambda r: r.name.lower()):
        real = str(repo.path.resolve())
        session_open = real in live
        copy = repo.path / copy_rel
        before = copy.read_text(errors="replace") if copy.exists() else None
        action = "current" if before == expected else ("would update" if args.dry_run else "updated")
        stub_action = agents_action = "dry-run"
        if not args.dry_run:
            if before != expected:
                copy.parent.mkdir(parents=True, exist_ok=True)
                copy.write_text(expected, encoding="utf-8")
            stub_action = ensure_stub(repo.path, header, stub_rel, copy_rel)
            agents_action = ensure_agents(repo.path, agents_rel, block, g["agents_begin"], g["agents_end"])
        # After the write on a real run, so it names only what the sync could not fix.
        warning = stub_warning(repo.path, stub_rel, copy_rel)
        paths = [stub_rel, copy_rel, agents_rel]
        ignored = [p for p in paths if wl.git_ignored(repo.path, p)]
        commit = "skipped"
        if session_open:
            commit = "deferred: session open"
        elif not args.dry_run:
            subprocess.run(["git", "add", *paths], cwd=repo.path, capture_output=True)
            if subprocess.run(["git", "diff", "--cached", "--quiet", "--", *paths], cwd=repo.path).returncode != 0:
                msg = f"chore: sync agent rules from spine@{sha}"
                if subprocess.run(["git", "commit", "-q", "-m", msg, "--", *paths], cwd=repo.path).returncode == 0:
                    if args.no_push:
                        commit = "committed"
                    elif subprocess.run(["git", "push", "-q"], cwd=repo.path, capture_output=True).returncode == 0:
                        commit = "committed + pushed"
                    else:
                        commit = push_with_recovery(repo.path)
                else:
                    commit = "commit failed (a repo-side gate may have refused it; read that before re-running)"
            else:
                commit = "no diff"
        rows.append({"repo": repo.name, "path": str(repo.path), "rules": action, "stub": stub_action,
                     "agents": agents_action, "ignored": ignored, "commit": commit, "warn": warning})

    if args.json:
        print(json.dumps({"sync_rules": rows}, indent=2))
    else:
        if not rows:
            print("no sync targets (see workspace.toml [[repos]] and the workspace roots)")
        for r in rows:
            ign = f" ignored={','.join(r['ignored'])}" if r["ignored"] else ""
            warn = f"; WARN {r['warn']}" if r["warn"] else ""
            print(f"{r['repo']}: {r['rules']}; {r['stub']}; {r['agents']}; {r['commit']}{ign}{warn}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
