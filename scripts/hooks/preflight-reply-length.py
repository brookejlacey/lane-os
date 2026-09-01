#!/usr/bin/env python3
"""UserPromptSubmit hook: the INSTRUCTING half of the reply-length pair.

A Stop hook can measure drift. It cannot prevent the reply it measures, because by the
time it fires the reply exists and has been paid for. This hook runs when the human
submits a prompt, before the model generates anything, and injects one line of context.

  advisory-reply-length.py  (Stop)             measures every reply -> outputs/reply-length.jsonl
  this file                 (UserPromptSubmit) reads that log, speaks ONLY when it shows drift

That conditioning is the point. The rule already lives in the always-loaded constitution,
so a reminder on every turn buys nothing but tokens; what decays is adherence deep into a
long session. So this stays silent while the recent replies are inside the rule and
speaks once they are not: zero tokens on a well-behaved session, one line on a drifting
one.

Carve-outs match the Stop hook exactly (an explicit ask for detail; a long-form desk).
audit-cheap.sh Check 14 asserts the two halves still share their limit.

Self-test: python3 scripts/hooks/preflight-reply-length.py --self-test
"""
import json
import os
import re
import sys
from pathlib import Path

# Kept identical to advisory-reply-length.py.
WORD_LIMIT = 220
LONG_FORM_DESKS = [d.strip() for d in os.environ.get("LANE_OS_LONG_FORM_DESKS", "").split(",") if d.strip()]
DETAIL_ASK = re.compile(
    r"\b(verbose|detailed|in detail|long form|long-form|walk me through|"
    r"explain (?:the whole|it all|everything)|deep dive|thorough)\b", re.I)

LOG = Path(__file__).resolve().parent.parent.parent / "outputs" / "reply-length.jsonl"

# How many recent replies to consider, and how many of them must be over to speak up.
WINDOW = 4
TRIGGER = 2

REMINDER = (
    "REPLY-LENGTH PRE-CHECK. The last few replies in this session ran long "
    "({over} of {seen} over {limit} words). Before answering: bullets, one fact per "
    "line, about 10 lines, and delete every line that does not change what the reader "
    "does next. Do not restate an answer you already gave in a shorter form; that renders "
    "the same fact twice. Lifted if this message asks for detail."
)


def in_long_form_desk(cwd):
    return any(f"desks/{d}" in (cwd or "") for d in LONG_FORM_DESKS)


def recent(session_id):
    """Recent replies for this session as (words, kinds), oldest first."""
    if not LOG.exists():
        return []
    rows = []
    try:
        with LOG.open("r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if session_id and row.get("session") != session_id:
                    continue
                words = row.get("words")
                if isinstance(words, int):
                    rows.append((words, row.get("kinds") or []))
    except OSError:
        return []
    # Very short replies are acknowledgements, not answers; counting them as "inside the
    # rule" would let a long/short alternation hide real drift.
    return [r for r in rows if r[0] >= 25][-WINDOW:]


def verdict(counts, prompt, cwd):
    """Return the reminder string, or None to stay silent."""
    if in_long_form_desk(cwd) or DETAIL_ASK.search(prompt or ""):
        return None
    if not counts:
        return None
    over = sum(1 for w, _ in counts if w > WORD_LIMIT)
    narrated = any("narrates its own process" in k for _, kinds in counts for k in kinds)
    if over < TRIGGER and not narrated:
        return None
    parts = []
    if over >= TRIGGER:
        parts.append(REMINDER.format(over=over, seen=len(counts), limit=WORD_LIMIT))
    if narrated:
        parts.append("A recent reply narrated its own process. State the corrected fact and "
                     "continue: no apology wrapper, no debugging journey.")
    return " ".join(parts)


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    message = verdict(recent(payload.get("session_id") or ""),
                      payload.get("prompt") or "",
                      payload.get("cwd") or os.getcwd())
    if message:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "UserPromptSubmit",
                                                 "additionalContext": message}}))
    return 0


def self_test():
    """Assert it STAYS SILENT when it should, which is the half that fails open."""
    ok = True

    def check(name, got, want):
        nonlocal ok
        if bool(got) != want:
            print(f"  FAIL  {name}: expected {'a reminder' if want else 'silence'}, got {got!r}")
            ok = False
        else:
            print(f"  ok    {name}")

    def r(*words):
        return [(w, []) for w in words]

    global LONG_FORM_DESKS
    LONG_FORM_DESKS = ["journal"]
    NARR = [(90, []), (100, ["reply narrates its own process"])]
    check("silent with no history", verdict([], "hi", "/repos/spine"), False)
    check("silent when replies are short", verdict(r(80, 90, 100, 110), "hi", "/repos/spine"), False)
    check("silent on one long reply", verdict(r(80, 300, 90, 100), "hi", "/repos/spine"), False)
    check("fires on two long replies", verdict(r(300, 90, 280, 100), "hi", "/repos/spine"), True)
    check("silent when detail is asked", verdict(r(300, 280, 290, 300), "walk me through it", "/repos/spine"), False)
    check("silent in a long-form desk", verdict(r(300, 280, 290, 300), "hi", "/repos/spine/desks/journal"), False)
    check("ignores acknowledgements", verdict(r(300, 4, 280, 6), "hi", "/repos/spine"), True)
    check("fires on narration even when short", verdict(NARR, "hi", "/repos/spine"), True)
    check("narration still yields to a detail ask", verdict(NARR, "walk me through it", "/repos/spine"), False)
    print("preflight-reply-length: PASS" if ok else "preflight-reply-length: FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        sys.exit(self_test())
    sys.exit(main())
