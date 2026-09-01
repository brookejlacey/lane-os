#!/usr/bin/env python3
"""Publish the cleared slice of a lane into a repo an outside reader sees.

A collaborator, a client or a partner reads a repo through their own agent and asks it
questions. They never write to your spine and never open it. So the repo they read has
to be the actual working corpus, minus what they must not see. This script produces it.

Three rules, in order of how much they matter:

1. ALLOWLIST THE PATHS, DENY-LIST THE REST. Named folders of one lane publish whole.
   Everything outside the lane is unreachable: nothing from brain/, memory/ or a desk can
   be reached at all, because the lane path is the root of the walk.
2. FAIL CLOSED ON CONTENT. Every byte about to be written is scanned against the deny
   patterns. One hit aborts the whole publish and writes nothing, naming the file, the
   line and the reason. A scrub that stripped silently would let a near-miss through
   unnoticed. Refusing makes the operator look at it.
3. ONLY THIS SCRIPT COMMITS THERE, AND ONLY WHAT IT WROTE. It stages an allowlist, never
   `git add -A`, and refuses to commit if any file it did not write is present. It also
   installs scripts/hooks/shared-repo-pre-commit.sh into the target as a second lock,
   and the rules sync derives its deny list from the AUDIENCES table below, so a repo
   named here can never receive the constitution.

After the push it confirms against origin, not against its own exit code: a publisher
that cannot see its own output is not finished.

Usage:
  python3 scripts/publish-shared-repo.py <audience>             publish, commit, push
  python3 scripts/publish-shared-repo.py <audience> --dry-run   scan and report, write nothing

The target checkout is <workspace root>/<audience>, or LANE_OS_SHARED_TARGET if set.
"""

from __future__ import annotations

import argparse
import datetime
import os
import pathlib
import re
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import workspace_lib as wl  # noqa: E402

SPINE = wl.spine_root()
MANIFEST_NAME = ".published-manifest"   # what this script published last time
INBOX_DIR = "inbox"                      # the reader writes here; never swept, never overwritten

# Patterns that apply to every audience. A hit aborts the publish.
SHARED_DENY = [
    (r"(?<![A-Za-z0-9-])sk-[A-Za-z0-9_-]{20,}|ghp_[A-Za-z0-9]{30,}|AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----",
     "a credential"),
    (r"\bINTERNAL ONLY\b|\bDO NOT PUBLISH\b", "marked internal by its author"),
    (r"desks/[a-z-]+/|brain/[A-Z_]+\.md|memory/[a-z_-]+\.md", "a path into the private spine"),
    (r"routing number|account number|\bEIN\b[:#]?\s*\d", "banking or tax identifiers"),
]

# One audience = one outside reader = one repo. The KEY is the repo name, which is also
# what workspace_lib.published_audience_names() reads to deny the rules sync.
AUDIENCES = {
    # An invented example: a partner who reads the example-app lane's docs and decisions.
    "example-partner-docs": {
        "lane": "projects/example-app",
        # source folder inside the lane -> destination folder in the shared repo ("" = root)
        "allow_dirs": {"docs": "", "decisions": "decisions"},
        "allow_root_files": {"STATUS.md": "status.md"},
        "deny_dirs": {"legal", "finances", "archive", "drafts"},
        "deny_files": {"MEMORY.md"},
        # audience-specific patterns, on top of SHARED_DENY
        "deny": [
            (r"\bpricing floor\b|\bwalk-away price\b", "negotiation position"),
            (r"\bcandidate\b.*\b(reject|pass on)\b", "a hiring judgment about a person"),
        ],
    },
}


def select(name: str) -> dict:
    if name not in AUDIENCES:
        raise SystemExit(f"unknown audience {name!r}. Known: {', '.join(sorted(AUDIENCES))}")
    cfg = dict(AUDIENCES[name])
    cfg["name"] = name
    cfg["lane_path"] = SPINE / cfg["lane"]
    cfg["deny_dirs"] = set(cfg.get("deny_dirs", ()))
    cfg["deny_files"] = set(cfg.get("deny_files", ()))
    cfg["deny_compiled"] = [(re.compile(p, re.IGNORECASE), why)
                            for p, why in SHARED_DENY + list(cfg.get("deny", []))]
    env = os.environ.get("LANE_OS_SHARED_TARGET")
    if env:
        cfg["target"] = pathlib.Path(env).expanduser()
    else:
        for root in wl.workspace_roots():
            if (root / name / ".git").is_dir():
                cfg["target"] = root / name
                break
        else:
            roots = wl.workspace_roots()
            cfg["target"] = (roots[0] if roots else pathlib.Path.home() / "repos") / name
    return cfg


def scrub_check(text: str, label: str, cfg: dict) -> list[str]:
    findings = []
    for pattern, reason in cfg["deny_compiled"]:
        for match in pattern.finditer(text):
            snippet = text[max(0, match.start() - 40):match.end() + 40].replace("\n", " ")
            line = text[:match.start()].count("\n") + 1
            findings.append(f"  {label}:{line}  [{reason}]  ...{snippet.strip()}...")
    return findings


def collect(cfg: dict) -> dict[str, pathlib.Path]:
    """Map destination path -> source path."""
    out: dict[str, pathlib.Path] = {}
    lane = cfg["lane_path"]
    for folder, dest_dir in cfg["allow_dirs"].items():
        base = lane / folder
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            if not path.is_file() or path.suffix.lower() != ".md":
                continue
            if any(part in cfg["deny_dirs"] for part in path.relative_to(lane).parts):
                continue
            if path.name in cfg["deny_files"]:
                continue
            name = path.relative_to(base).as_posix()
            dest = f"{dest_dir}/{name}" if dest_dir else name
            if dest in out and out[dest] != path:
                raise SystemExit(f"destination collision on {dest!r}: {out[dest]} and {path}")
            out[dest] = path
    for filename, dest in cfg["allow_root_files"].items():
        path = lane / filename
        if path.is_file():
            out[dest] = path
    return out


def ensure_repo_hook(target: pathlib.Path) -> None:
    """Keep the target repo's own pre-commit lock installed. .git/hooks is not version
    controlled, so it would be lost on a re-clone; installing on every run means it
    cannot quietly go missing."""
    if not (target / ".git").is_dir():
        print(f"  {target} is not a checkout yet; skipping the pre-commit lock")
        return
    source = SPINE / "scripts" / "hooks" / "shared-repo-pre-commit.sh"
    hook = target / ".git" / "hooks" / "pre-commit"
    wanted = source.read_text(encoding="utf-8")
    if not hook.is_file() or hook.read_text(encoding="utf-8", errors="replace") != wanted:
        hook.parent.mkdir(parents=True, exist_ok=True)
        hook.write_text(wanted, encoding="utf-8")
        hook.chmod(0o755)
        print("  installed the repo's pre-commit lock")


def run(cmd: list[str], cwd: pathlib.Path) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("audience", choices=sorted(AUDIENCES))
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    cfg = select(args.audience)
    target: pathlib.Path = cfg["target"]
    if not args.dry_run and not (target / ".git").is_dir():
        print(f"target repo missing: {target}", file=sys.stderr)
        return 1

    ensure_repo_hook(target)
    mapping = collect(cfg)
    if not mapping:
        print(f"nothing to publish from {cfg['lane']}", file=sys.stderr)
        return 1

    stamp = datetime.date.today().isoformat()
    outgoing: dict[str, str] = {}
    findings: list[str] = []
    for dest, src in sorted(mapping.items()):
        text = src.read_text(encoding="utf-8", errors="replace").strip()
        findings.extend(scrub_check(text, dest, cfg))
        text += f"\n\n---\n\n*Source: `{src.relative_to(SPINE).as_posix()}`. Published {stamp}.*\n"
        outgoing[dest] = text

    if findings:
        print("PUBLISH ABORTED. Nothing was written.\n", file=sys.stderr)
        print(f"{len(findings)} deny-pattern hit(s):\n", file=sys.stderr)
        for f in findings[:60]:
            print(f, file=sys.stderr)
        print("\nFix the source, or add the file to deny_files / deny_dirs. Do not loosen a "
              "deny rule to get past this.", file=sys.stderr)
        return 2
    print(f"scrub clean: {len(outgoing)} file(s), 0 deny-pattern hits")

    if args.dry_run:
        for dest in sorted(outgoing):
            print(f"  would publish  {dest}")
        return 0

    # Reset to origin before writing, never rebase: every file here is DERIVED, so two
    # hosts publishing the same lane produce competing commits with identical content.
    # Throw away local generated state, take origin (which carries the reader's inbox
    # pushes), regenerate.
    run(["git", "fetch", "-q", "origin"], target)
    branch = run(["git", "rev-parse", "--abbrev-ref", "HEAD"], target).stdout.strip() or "main"
    if run(["git", "rev-parse", "--verify", f"origin/{branch}"], target).returncode == 0:
        run(["git", "reset", "--hard", "-q", f"origin/{branch}"], target)

    for dest, text in outgoing.items():
        path = target / dest
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    # A page whose source is gone must disappear. Only a file THIS script published
    # before is eligible; anything else is foreign and reaches the abort below.
    manifest_path = target / MANIFEST_NAME
    try:
        previously = set(manifest_path.read_text(encoding="utf-8").split())
    except FileNotFoundError:
        previously = set()
    for rel in sorted(previously - set(outgoing)):
        stale = target / rel
        if stale.is_file():
            stale.unlink()
            print(f"  removed  {rel}  (no longer in source)")
    manifest_path.write_text("\n".join(sorted(outgoing)) + "\n", encoding="utf-8")
    print(f"  published {len(outgoing)} file(s)")

    inbox = target / INBOX_DIR
    theirs = sorted(f.relative_to(target).as_posix() for f in inbox.rglob("*")
                    if f.is_file() and f.name != "README.md") if inbox.is_dir() else []
    if theirs:
        print(f"  INBOX: {len(theirs)} file(s) waiting from the reader:")
        for name in theirs:
            print(f"    {name}")

    # An allowlisted commit, not `git add -A`. Stage only what this script generated,
    # then refuse to commit if anything else is present.
    expected = set(outgoing) | {".gitignore", MANIFEST_NAME}
    present = set()
    for path in target.rglob("*"):
        rel = path.relative_to(target).as_posix()
        if path.is_file() and not rel.startswith(".git/") and rel != ".git" and not rel.startswith(INBOX_DIR + "/"):
            present.add(rel)
    foreign = sorted(present - expected)
    if foreign:
        print("PUBLISH ABORTED. Nothing was committed.\n", file=sys.stderr)
        print(f"{len(foreign)} file(s) in {target} were not written by this script:", file=sys.stderr)
        for name in foreign[:25]:
            print(f"  {name}", file=sys.stderr)
        print("\nSomething else wrote into a repo that is read outside the workspace. Find what, "
              "remove the file, and deny that writer.", file=sys.stderr)
        return 3

    for name in sorted(expected):
        if (target / name).exists():
            run(["git", "add", "--", name], target)
    if run(["git", "diff", "--cached", "--quiet"], target).returncode == 0:
        print("no changes to publish")
        return 0
    commit = run(["git", "commit", "-q", "-m", f"publish: {cfg['lane']} {stamp}"], target)
    if commit.returncode != 0:
        print(f"commit failed: {commit.stderr.strip()}", file=sys.stderr)
        return 1
    if run(["git", "remote", "get-url", "origin"], target).returncode != 0:
        print("committed (no origin configured, nothing pushed)")
        return 0
    push = run(["git", "push", "-q"], target)
    if push.returncode != 0:
        print(f"push failed: {push.stderr.strip()}", file=sys.stderr)
        return 1
    head = run(["git", "rev-parse", "HEAD"], target).stdout.strip()
    remote = run(["git", "ls-remote", "origin", f"refs/heads/{branch}"], target).stdout.split()
    if not remote or remote[0] != head:
        print(f"PUSH DID NOT LAND: local {head[:7]}, remote {(remote[0][:7] if remote else 'none')}", file=sys.stderr)
        return 4
    print(f"pushed and confirmed on origin at {head[:7]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
