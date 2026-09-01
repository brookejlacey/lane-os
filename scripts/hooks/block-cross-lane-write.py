#!/usr/bin/env python3
"""Lane OS PreToolUse hook: enforce the write-lane invariant mechanically.

The rule (global/CLAUDE.md): a session writes ONLY its own lane + brain/drafts/.
This hook resolves the write TARGET against the session's CWD lane and hard-blocks
out-of-lane writes (exit 2), so wrong-lane work becomes impossible instead of a rule
the model has to remember.

Lanes:
  - CODE lane: cwd is a code repo (a git repo that is not the spine). May write that
    repo, its spine/projects/<name>/ mirror, and brain/drafts/.
  - CODE lane, addressed by its mirror: cwd is spine/projects/<name>/. Opening a
    terminal there means "I am working that lane", not "I own the spine". It gets the
    mirror, the code repo of the same name (if one exists under a workspace root),
    and brain/drafts/. Without this rule, cd-ing one level deeper into the spine
    silently bought write access to memory/, global/, skills/ and brain/.
  - DESK lane: cwd is spine/desks/<desk>. May write that desk + brain/drafts/.
  - SPINE (workspace-root): cwd is the spine repo root or any other spine path. Owns
    the whole spine and the agent's own config dir (~/.claude), but may NOT hand-edit
    another repo's code.

Design: FAIL OPEN. Block only high-confidence cross-lane violations; on any
uncertainty (cannot resolve a path, unknown layout, escape hatch set) exit 0.
Temp paths (/tmp, $TMPDIR) are always allowed: scratch is nobody's lane.
Escape hatch: set LANE_GUARD_OFF=1 to disable. Note: it cannot see writes made via
Bash heredocs/redirects, so the routing reflex still backs it up.

A fail-open guard cannot report its own death: a broken guard and an approving guard
look identical from outside. That is why scripts/test-lanes.sh exists and why
audit-cheap's write-lane check runs it on every commit. If you edit this file, run
the test and confirm it still BLOCKS.

Register in settings.json as a PreToolUse hook matching Write|Edit|MultiEdit|NotebookEdit.
"""
import sys
import os
import json
import subprocess
import tempfile

HOME = os.path.expanduser("~")
# The agent's own config dir. A spine session legitimately maintains settings.json,
# hooks/ and the synced CLAUDE.md there, so it is spine, not "another repo's code".
AGENT_CFG = os.path.join(HOME, ".claude")


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


def is_temp_path(path):
    roots = {"/tmp", "/private/tmp", tempfile.gettempdir()}
    if os.environ.get("TMPDIR"):
        roots.add(os.environ["TMPDIR"])
    return any(under(path, root) for root in roots)


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


def workspace_roots():
    """Where code repos live. LANE_OS_WORKSPACE_ROOTS is a colon-separated override."""
    env = os.environ.get("LANE_OS_WORKSPACE_ROOTS")
    if env:
        return [rp(os.path.expanduser(p)) for p in env.split(":") if p]
    return [os.path.join(HOME, "repos"), os.path.join(HOME, "work")]


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


def repo_for_path(path, spine):
    """The code repo (a direct child of a workspace root) that contains path, or None."""
    for root in workspace_roots():
        if not under(path, root):
            continue
        rel = os.path.relpath(rp(path), rp(root)).split(os.sep)
        if not rel or rel[0] in ("", "."):
            continue
        candidate = os.path.join(root, rel[0])
        if under(candidate, spine):
            return None
        if os.path.isdir(os.path.join(candidate, ".git")):
            return candidate
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

    cwd = rp(data.get("cwd") or os.getcwd())
    if not os.path.isabs(target):
        target = os.path.join(cwd, target)
    target = rp(target)

    SPINE = find_spine()
    if not SPINE:
        sys.exit(0)  # no spine on this machine -> fail open

    drafts = os.path.join(SPINE, "brain", "drafts")
    # Everyone may always stage to brain/drafts (the shared inbox).
    if under(target, drafts):
        sys.exit(0)
    # Scratch is nobody's lane, unless a workspace root itself lives under the temp
    # dir (the test harness does exactly that), in which case the repo rules win.
    if is_temp_path(target) and repo_for_path(target, SPINE) is None:
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

    # cwd is inside the spine. A project mirror, a desk, or workspace-root?
    rel = os.path.relpath(cwd, SPINE).split(os.sep)

    if len(rel) >= 2 and rel[0] == "projects":
        proj = rel[1]
        if under(target, os.path.join(SPINE, "projects", proj)):
            sys.exit(0)  # own mirror
        for root in workspace_roots():
            if under(target, os.path.join(root, proj)):
                sys.exit(0)  # the code repo of the same name
        if under(target, SPINE):
            block(
                "a CODE session addressed by its mirror (cwd projects/" + proj + ") may "
                "write only projects/" + proj + "/, the " + proj + " repo, and "
                "brain/drafts/. Being inside the spine does not make this a spine "
                "session. Stage it in brain/drafts/, or open a session at the spine root."
            )
        if repo_for_path(target, SPINE):
            block(
                "a CODE session (cwd projects/" + proj + ") is writing outside its lane: "
                + target + ". Open a session in the repo that owns this file."
            )
        sys.exit(0)

    if len(rel) >= 2 and rel[0] == "desks":
        desk = rel[1]
        if under(target, os.path.join(SPINE, "desks", desk)):
            sys.exit(0)
        block(
            "a DESK session (desks/" + desk + ") may write only its own desk + "
            "brain/drafts/. This targets " + target + ". Stage in brain/drafts/, or "
            "open the right lane."
        )

    # SPINE (workspace-root): owns the whole spine and the agent config dir.
    if under(target, SPINE) or under(target, AGENT_CFG):
        sys.exit(0)
    # Machine-level ops (dotfiles, launchd plists, scratch) are not "another repo's
    # code" and must not be blocked. The only spine violation is hand-editing a code
    # repo under a workspace root, so require that before blocking.
    if repo_for_path(target, SPINE) is None:
        sys.exit(0)
    block(
        "a SPINE session owns the spine, not product code. This targets " + target
        + ". cd into that repo and work there (code goes in the code lane)."
    )


main()
