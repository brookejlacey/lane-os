#!/usr/bin/env python3
"""Lane OS PreToolUse hook: enforce the write-lane invariant mechanically.

The rule (global/CLAUDE.md): a session writes ONLY its own lane + brain/drafts/.
This hook resolves the write TARGET against the session's CWD lane and hard-blocks
out-of-lane writes (exit 2), so wrong-lane work becomes impossible instead of a rule
the model has to remember.

Lanes:
  - CODE lane: cwd is a code repo (a git repo that is not the spine). May write that
    repo, its spine/projects/<name>/ mirror, and brain/drafts/.
  - DESK lane: cwd is spine/desks/<desk>. May write that desk + brain/drafts/.
  - SPINE (workspace-root): cwd is the spine repo (not under desks/). Owns the whole
    spine, but may NOT hand-edit another repo's code.

Design: FAIL OPEN. Block only high-confidence cross-lane violations; on any
uncertainty (cannot resolve a path, unknown layout, escape hatch set) exit 0.
Escape hatch: set LANE_GUARD_OFF=1 to disable. Note: it cannot see writes made via
Bash heredocs/redirects, so the routing reflex still backs it up.

Register in settings.json as a PreToolUse hook matching Write|Edit|MultiEdit|NotebookEdit.
"""
import sys
import os
import json
import subprocess

HOME = os.path.expanduser("~")


def rp(p):
    try:
        return os.path.realpath(p)
    except Exception:
        return p


def under(path, base):
    if not path or not base:
        return False
    path, base = rp(path), rp(base)
    return path == base or path.startswith(base.rstrip("/") + "/")


def find_spine():
    env = os.environ.get("LANE_OS_ROOT")
    if env and os.path.isdir(os.path.join(env, ".git")):
        return rp(env)
    for c in (
        os.path.join(HOME, "work", "spine"),
        os.path.join(HOME, "repos", "spine"),
        os.path.join(HOME, "lane-os"),
        os.path.join(HOME, "repos", "lane-os"),
    ):
        if os.path.isdir(os.path.join(c, ".git")):
            return rp(c)
    return None


def git_toplevel(cwd):
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=cwd, capture_output=True, text=True, timeout=3,
        )
        if out.returncode == 0:
            return rp(out.stdout.strip())
    except Exception:
        pass
    return None


def block(msg):
    sys.stderr.write("BLOCKED (write-lane): " + msg + "\n")
    sys.exit(2)


def main():
    if os.environ.get("LANE_GUARD_OFF") == "1":
        sys.exit(0)
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    ti = data.get("tool_input", {}) or {}
    target = ti.get("file_path") or ti.get("notebook_path")
    if not isinstance(target, str) or not target:
        sys.exit(0)
    target = rp(target)

    cwd = rp(data.get("cwd") or os.getcwd())

    SPINE = find_spine()
    if not SPINE:
        sys.exit(0)  # no spine on this machine -> fail open

    drafts = os.path.join(SPINE, "brain", "drafts")
    # Everyone may always stage to brain/drafts (the shared inbox).
    if under(target, drafts):
        sys.exit(0)

    cwd_in_spine = under(cwd, SPINE)

    if not cwd_in_spine:
        # CODE lane: cwd is a code repo somewhere on disk.
        repo_root = git_toplevel(cwd)
        if not repo_root:
            sys.exit(0)  # unknown layout -> fail open
        repo_name = os.path.basename(repo_root)

        if under(target, repo_root):
            sys.exit(0)  # own repo
        if under(target, os.path.join(SPINE, "projects", repo_name)):
            sys.exit(0)  # own mirror
        if under(target, SPINE):
            block(
                "a CODE session (cwd " + repo_name + ") may write only its own repo, "
                "its projects/" + repo_name + "/ mirror, and brain/drafts/. This "
                "targets the spine. Stage it in brain/drafts/, or open a spine session."
            )
        block(
            "a CODE session (cwd " + repo_name + ") is writing outside its lane: "
            + target + ". Open a session in the repo that owns this file."
        )

    # cwd is inside the spine. Desk or workspace-root?
    rel = os.path.relpath(cwd, SPINE).split(os.sep)
    if len(rel) >= 2 and rel[0] == "desks":
        desk = rel[1]
        if under(target, os.path.join(SPINE, "desks", desk)):
            sys.exit(0)
        block(
            "a DESK session (desks/" + desk + ") may write only its own desk + "
            "brain/drafts/. This targets " + target + ". Stage in brain/drafts/, or "
            "open the right lane."
        )

    # SPINE (workspace-root): owns the whole spine.
    if under(target, SPINE):
        sys.exit(0)
    block(
        "a SPINE session owns the spine, not product code. This targets " + target
        + ". cd into that repo and work there (code goes in the code lane)."
    )


main()
