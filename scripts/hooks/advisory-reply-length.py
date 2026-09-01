#!/usr/bin/env python3
"""Stop hook: the MEASURING half of the reply-length pair. It never speaks.

THE GAP THIS CLOSES
-------------------
Every other hook gates a TOOL CALL. Sort a session's rule misses by where they happened
and most are REPORTING failures, not doing failures: the execution layer held (the lane
guard fired, the commit gate blocked), and the reply itself drifted, because nothing
watches the reply. This hook does.

WHY IT ONLY MEASURES
--------------------
A Stop hook fires after the reply exists and has been paid for. Anything it says can
only be acted on by a second reply, which either restates the answer (rendering the same
fact twice) or spends a turn saying nothing. So this half MEASURES and does not speak:
it reads the transcript, counts the prose words of the final assistant message, notes
whether it narrated its own process, and appends one JSON row to
outputs/reply-length.jsonl.

`preflight-reply-length.py` (UserPromptSubmit) reads that log and instructs BEFORE the
next reply, which is the half that can actually change the output. Set
REPLY_LENGTH_ADVISORY=1 to make this half print its findings, for debugging.

The two halves keep the same limit and the same carve-outs on purpose: two halves of one
rule that disagree about when the rule applies are worse than either alone.
audit-cheap.sh Check 14 asserts they still agree.

Self-test: python3 scripts/hooks/advisory-reply-length.py --self-test
"""
import datetime as _dt
import json
import os
import re
import sys
from pathlib import Path

# Kept identical to preflight-reply-length.py.
WORD_LIMIT = 220          # generous: the rule says ~10 lines; this catches a genuine wall
# Desks where long is the correct register. Comma-separated desk names, e.g. "journal".
LONG_FORM_DESKS = [d.strip() for d in os.environ.get("LANE_OS_LONG_FORM_DESKS", "").split(",") if d.strip()]
DETAIL_ASK = re.compile(
    r"\b(verbose|detailed|in detail|long form|long-form|walk me through|"
    r"explain (?:the whole|it all|everything)|deep dive|thorough)\b", re.I)
# Self-narration the reply rule bans: the debugging journey and the apology wrapper.
NARRATION = re.compile(
    r"\b(i was wrong|my earlier|to correct myself|i apologi[sz]e|sorry (?:about|for) that|"
    r"failed attempt|turns out i|i should have|let me correct)\b", re.I)
FENCE = re.compile(r"```.*?```", re.S)

LOG = Path(__file__).resolve().parent.parent.parent / "outputs" / "reply-length.jsonl"


def in_long_form_desk(cwd):
    return any(f"desks/{d}" in (cwd or "") for d in LONG_FORM_DESKS)


def text_of(message):
    """Assistant messages carry content as a string or as a list of typed blocks."""
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(b.get("text", "") for b in content
                         if isinstance(b, dict) and b.get("type") == "text")
    return ""


def read_transcript(path):
    """Return (last assistant text, joined recent user text)."""
    last_assistant, users = "", []
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                msg = row.get("message") or {}
                role = msg.get("role") or row.get("type")
                t = text_of(msg)
                if role == "assistant" and t.strip():
                    last_assistant = t
                elif role == "user" and t.strip():
                    users.append(t)
    except OSError:
        return "", ""
    return last_assistant, "\n".join(users[-3:])


def prose_words(reply):
    """Count only the prose, not fenced blocks. A paste-ready message or a command the
    human asked for IS the deliverable, so counting it as verbosity fires on exactly the
    replies that were correct."""
    return len(FENCE.sub(" ", reply).split())


def assess(reply, recent_user, cwd):
    """Return a list of findings. Empty means the reply is inside the rules."""
    findings = []
    if in_long_form_desk(cwd) or DETAIL_ASK.search(recent_user or ""):
        return findings
    words = prose_words(reply)
    if words > WORD_LIMIT:
        findings.append(f"reply is {words} words; the rule asks for bullets and about 10 lines. "
                        "Delete every line that does not change what the reader does next.")
    hit = NARRATION.search(reply)
    if hit:
        findings.append(f"reply narrates its own process ({hit.group(0)!r}); state the corrected "
                        "fact and continue, no apology wrapper and no debugging journey.")
    return findings


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    transcript = payload.get("transcript_path") or ""
    cwd = payload.get("cwd") or os.getcwd()
    if not transcript:
        return 0
    reply, recent_user = read_transcript(transcript)
    if not reply.strip():
        return 0
    findings = assess(reply, recent_user, cwd)
    try:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with LOG.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({
                "ts": payload.get("timestamp") or _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
                "session": payload.get("session_id") or "",
                "words": prose_words(reply),
                "findings": len(findings),
                # Kinds, not just a count, so the pre-check can say WHICH habit is drifting.
                "kinds": [f.split(";")[0].split("(")[0].strip()[:40] for f in findings],
            }) + "\n")
    except OSError:
        pass
    if findings and os.environ.get("REPLY_LENGTH_ADVISORY") == "1":
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "Stop",
                          "additionalContext": "REPLY-LENGTH ADVISORY. " + " ".join(findings)}}))
    return 0


def self_test():
    fails = 0

    def check(name, ok):
        nonlocal fails
        print(f"  {'ok  ' if ok else 'FAIL'}  {name}")
        fails += 0 if ok else 1

    global LONG_FORM_DESKS
    LONG_FORM_DESKS = ["journal"]
    wall = " ".join(["word"] * 400)
    check("a 400-word reply is flagged", len(assess(wall, "what is the status", "/repos/spine")) == 1)
    check("a short reply is clean", assess("Done. Pushed.", "ship it", "/repos/spine") == [])
    check("an explicit ask for detail lifts the cap", assess(wall, "give me a detailed verbose answer", "/repos/spine") == [])
    check("walk-me-through lifts the cap", assess(wall, "walk me through the whole thing", "/repos/spine") == [])
    check("a long-form desk is standing-lifted", assess(wall, "how is it going", "/repos/spine/desks/journal") == [])
    check("a fenced block does not count as verbosity", assess("Here:\n```\n" + wall + "\n```", "give me the command", "/repos/spine") == [])
    check("self-narration is flagged even in a short reply",
          any("narrates" in f for f in assess("I was wrong about the count.", "ok", "/repos/spine")))
    check("a long reply with narration reports both", len(assess(wall + " my earlier claim was off", "status?", "/repos/spine")) == 2)
    check("list-shaped assistant content is read",
          text_of({"content": [{"type": "text", "text": "hi"}, {"type": "tool_use", "id": "x"}]}) == "hi")
    print(f"advisory-reply-length: {'all 9 assertions pass' if not fails else f'{fails} FAILED'}")
    return 1 if fails else 0


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        sys.exit(self_test())
    sys.exit(main())
