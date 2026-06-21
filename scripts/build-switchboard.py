#!/usr/bin/env python3
"""Build a LOCAL switchboard: a per-machine snapshot of what moved in every lane,
so any session can glance at what the OTHER windows have been doing.

Writes switchboard/state.json and switchboard/SWITCHBOARD.html (both gitignored).
Best-effort and read-only over your repos; safe to run from the SessionStart hook.

This is intentionally simple: it lists each code lane's latest commit and each
desk's last-modified time. Extend it to taste.
"""
import os
import json
import subprocess
import glob

HOME = os.path.expanduser("~")
SPINE = os.environ.get("LANE_OS_ROOT") or os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)


def last_commit(path):
    try:
        out = subprocess.run(
            ["git", "-C", path, "log", "-1", "--format=%h %cr %s"],
            capture_output=True, text=True, timeout=4,
        )
        if out.returncode == 0:
            return out.stdout.strip()
    except Exception:
        pass
    return None


def main():
    lanes = []
    # code lanes: each projects/<name> mirrors a repo; find the repo if present
    for mirror in sorted(glob.glob(os.path.join(SPINE, "projects", "*"))):
        name = os.path.basename(mirror)
        if name.startswith("_"):
            continue
        repo = None
        for base in (os.path.join(HOME, "repos", name), os.path.join(HOME, "work", name)):
            if os.path.isdir(os.path.join(base, ".git")):
                repo = base
                break
        head = last_commit(repo) if repo else None
        lanes.append({"type": "code", "name": name, "head": head})
    # desks
    for desk in sorted(glob.glob(os.path.join(SPINE, "desks", "*"))):
        name = os.path.basename(desk)
        if name.startswith("_"):
            continue
        log = os.path.join(desk, "LOG.md")
        mtime = os.path.getmtime(log) if os.path.exists(log) else None
        lanes.append({"type": "desk", "name": name, "head": mtime})

    out_dir = os.path.join(SPINE, "switchboard")
    os.makedirs(out_dir, exist_ok=True)
    state = {"lanes": lanes}
    json.dump(state, open(os.path.join(out_dir, "state.json"), "w"), indent=2)

    rows = "".join(
        "<tr><td>{}</td><td>{}</td><td>{}</td></tr>".format(
            l["type"], l["name"], l.get("head") or ""
        )
        for l in lanes
    )
    html = (
        "<!doctype html><meta charset=utf-8><title>Switchboard</title>"
        "<style>body{font-family:ui-monospace,monospace;margin:2rem}"
        "table{border-collapse:collapse}td{border:1px solid #ccc;padding:.4rem .8rem}"
        "</style><h1>Switchboard</h1><table>"
        "<tr><th>type</th><th>lane</th><th>latest</th></tr>" + rows + "</table>"
    )
    open(os.path.join(out_dir, "SWITCHBOARD.html"), "w").write(html)


if __name__ == "__main__":
    main()
