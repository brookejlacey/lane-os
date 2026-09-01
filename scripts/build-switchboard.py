#!/usr/bin/env python3
"""build-switchboard.py: the cross-lane awareness map.

Walks every lane (code repos under your workspace roots, plus the topic desks) and writes
one always-current view of what each lane is and when it last moved, so a session in one
window can see what happened elsewhere without any lane writing into another. It only
ever writes switchboard/; lanes only read it, so there is no git race.

Outputs (both gitignored, per machine):
  switchboard/SWITCHBOARD.html  a row per lane: freshness, last human commit, focus
  switchboard/state.json        {built, built_human, lanes:{name:{head,ts,subject,focus,kind}}}

Two things it does beyond `git log -1`:

  * Freshness is measured on the newest NON-BOT commit. The rules sync touches every
    lane whenever the constitution changes, so without this filter each sync lights up
    "moved <24h" on lanes nobody has opened in weeks, which is exactly the signal this
    page exists to carry.
  * Each lane carries a `focus`: the newest dated `## YYYY-MM-DD ...` heading in its
    spine-facing state file (projects/<name>/STATUS.md, or desks/<name>/LOG.md). That is
    "what is this lane chewing on", which exists in a session or a STATUS note before it
    is ever a commit. Zero adoption cost: dated headings already exist in most STATUS
    files. A neighbouring session reads it and messages that lane instead of
    re-deriving the work.

Run from the SessionStart hook (best-effort, backgrounded) and on any schedule you like.
Env: LANE_OS_ROOT (spine), LANE_OS_WORKSPACE_ROOTS (colon-separated dirs holding repos).
"""
import html
import json
import os
import re
import subprocess
from datetime import datetime, timezone

HOME = os.path.expanduser("~")
SPINE = os.path.realpath(os.environ.get("LANE_OS_ROOT") or os.path.join(
    os.path.dirname(os.path.abspath(__file__)), ".."))
OUT_DIR = os.path.join(SPINE, "switchboard")

IDLE_AFTER = 14 * 86400   # a lane with no human commit in this long reads as idle, not dead

# Automated commits that are not "a lane moved". Conservative on purpose: under-filtering
# costs a stale-looking row, over-filtering hides real work.
BOT_SUBJECTS = (
    r"^chore(\([^)]+\))?: sync (agent|global) rules",
    r"^switchboard: ",
    r"^auto-",
)

DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
FOCUS_RE = re.compile(r"^##\s+(\d{4}-\d{2}-\d{2})?\s*[·:\-]?\s*(.+?)\s*$", re.M)


def workspace_roots():
    env = os.environ.get("LANE_OS_WORKSPACE_ROOTS")
    if env:
        return [os.path.realpath(os.path.expanduser(p)) for p in env.split(":") if p]
    return [os.path.join(HOME, "repos"), os.path.join(HOME, "work")]


def git(repo, *args):
    try:
        return subprocess.run(["git", "-C", repo, *args], capture_output=True,
                              text=True, timeout=15).stdout.strip()
    except Exception:
        return ""


def last_human_commit(repo, *pathspec):
    """Newest commit that isn't automation. Falls back to raw HEAD when a lane has
    nothing but bot commits, so the row still shows something truthful."""
    grep = []
    for pat in BOT_SUBJECTS:
        grep += ["--grep", pat]
    base = ["log", "-1", "--extended-regexp", "--invert-grep", *grep]
    tail = ["--", *pathspec] if pathspec else []
    ts = git(repo, *base, "--format=%ct", *tail)
    subj = git(repo, *base, "--format=%s", *tail)
    if ts:
        return ts, subj, False
    return git(repo, "log", "-1", "--format=%ct", *tail), git(repo, "log", "-1", "--format=%s", *tail), True


def lane_focus(kind, name):
    """The newest dated heading in this lane's state file, or None. An undated heading is
    a section label and reports nothing about what the lane is on right now."""
    if kind == "desk":
        candidates = [os.path.join(SPINE, "desks", name, "LOG.md")]
    else:
        candidates = [os.path.join(SPINE, "projects", name, "STATUS.md")]
    for path in candidates:
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except OSError:
            continue
        dated = []
        for m in FOCUS_RE.finditer(text):
            date, title = m.group(1), (m.group(2) or "").strip()
            if not date:
                inline = DATE_RE.search(title)
                if not inline:
                    continue
                date = inline.group(0)
            if title:
                dated.append((date, title))
        if dated:
            return max(dated)[1]
    return None


def to_int(ts):
    try:
        return int(ts) if ts else 0
    except ValueError:
        return 0


def discover():
    lanes = []
    seen = set()
    for root in workspace_roots():
        if not os.path.isdir(root):
            continue
        for name in sorted(os.listdir(root)):
            path = os.path.join(root, name)
            real = os.path.realpath(path)
            if name.startswith(".") or real == SPINE or real in seen:
                continue
            if not os.path.isdir(os.path.join(path, ".git")):
                continue
            seen.add(real)
            ts, subj, bot_only = last_human_commit(path)
            lanes.append({"name": name, "kind": "code", "path": path,
                          "head": git(path, "rev-parse", "--short", "HEAD"),
                          "ts": to_int(ts), "subject": subj,
                          "dirty": bool(git(path, "status", "--porcelain").strip()),
                          "bot_only": bot_only, "focus": lane_focus("code", name)})
    desks = os.path.join(SPINE, "desks")
    if os.path.isdir(desks):
        for d in sorted(os.listdir(desks)):
            p = os.path.join(desks, d)
            if d.startswith("_") or not os.path.isdir(p):
                continue
            ts, subj, bot_only = last_human_commit(SPINE, f"desks/{d}")
            lanes.append({"name": d, "kind": "desk", "path": p,
                          "head": git(SPINE, "rev-parse", "--short", "HEAD"),
                          "ts": to_int(ts), "subject": subj, "dirty": False,
                          "bot_only": bot_only, "focus": lane_focus("desk", d)})
    return lanes


def ago(ts, now):
    if not ts:
        return "never"
    secs = max(0, now - ts)
    if secs >= 86400:
        return f"{secs // 86400}d ago"
    if secs >= 3600:
        return f"{secs // 3600}h ago"
    return f"{max(1, secs // 60)}m ago"


def render_html(lanes, now):
    rows = []
    for l in sorted(lanes, key=lambda x: x["ts"], reverse=True):
        age = (now - l["ts"]) if l["ts"] else None
        moved = age is not None and age < 86400
        idle = age is None or age >= IDLE_AFTER
        badges = ""
        if moved:
            badges += '<span class="badge moved">moved &lt;24h</span>'
        if l.get("dirty"):
            badges += '<span class="badge dirty">uncommitted</span>'
        if idle:
            badges += '<span class="badge idle">idle</span>'
        focus = (f'<div class="focus">on: {html.escape(l["focus"][:110])}</div>' if l.get("focus") else "")
        rows.append(
            f'<tr{" class=idle" if idle else ""}>'
            f'<td class="nm">{html.escape(l["name"])}<span class="k">{l["kind"]}</span></td>'
            f'<td class="mono">{html.escape(ago(l["ts"], now))}</td>'
            f'<td>{html.escape((l["subject"] or "")[:90])} {badges}{focus}</td>'
            f'<td class="mono">{html.escape(l["head"] or "")}</td></tr>')
    built = datetime.fromtimestamp(now, timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M %Z")
    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Switchboard: all lanes</title><meta name="robots" content="noindex"/>
<style>
body{{margin:0;background:#faf8f3;color:#2a2a26;font-family:system-ui,sans-serif;font-size:16px}}
main{{max-width:920px;margin:0 auto;padding:40px 32px 70px}}
h1{{font-size:28px;margin:0 0 6px}} .sub{{color:#6b6a61;margin-bottom:24px}}
table{{border-collapse:collapse;width:100%}}
th,td{{text-align:left;padding:9px 10px;border-bottom:1px solid #e3dcca;vertical-align:top}}
th{{font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:#6b6a61}}
.mono{{font-family:ui-monospace,monospace;font-size:14px}} td.nm{{font-weight:600}}
.k{{font-size:10px;text-transform:uppercase;margin-left:8px;padding:1px 6px;border-radius:999px;background:#eee}}
.badge{{font-size:10px;text-transform:uppercase;padding:1px 7px;border-radius:999px;margin-left:6px;white-space:nowrap}}
.moved{{background:#dde9dd;color:#2f6b3f}} .dirty{{background:#f2e0d8;color:#8e3b20}} .idle{{background:#edeadf;color:#9a988c}}
tr.idle{{opacity:.7}} .focus{{color:#6b6a61;font-size:13.5px;margin-top:3px}}
.foot{{margin-top:22px;font-size:13px;color:#9a988c}}
</style></head><body><main>
<h1>What every lane is doing</h1>
<div class="sub">Read this at the top of a session to see what moved in the other windows. Generated read-only; lanes never write each other.</div>
<table><tr><th>Lane</th><th>Last move</th><th>Most recent human commit</th><th>HEAD</th></tr>
{''.join(rows)}
</table>
<div class="foot">Built {built}. Source: scripts/build-switchboard.py</div>
</main></body></html>"""


def main():
    now = int(datetime.now(timezone.utc).timestamp())
    lanes = discover()
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, "SWITCHBOARD.html"), "w") as f:
        f.write(render_html(lanes, now))
    state = {"built": now, "built_human": datetime.fromtimestamp(now, timezone.utc).isoformat(),
             "lanes": {l["name"]: {"head": l["head"], "ts": l["ts"], "subject": l["subject"],
                                   "focus": l.get("focus"), "kind": l["kind"],
                                   "bot_only": l.get("bot_only", False)} for l in lanes}}
    with open(os.path.join(OUT_DIR, "state.json"), "w") as f:
        json.dump(state, f, indent=2)
    print(f"switchboard: {len(lanes)} lanes -> {OUT_DIR}/SWITCHBOARD.html")


if __name__ == "__main__":
    main()
