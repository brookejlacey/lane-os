#!/usr/bin/env python3
"""The voice linter: thirteen mechanical checks that read a draft before a human does.

WHY A SEPARATE LINTER AND NOT "REVIEW YOUR OWN DRAFT"
----------------------------------------------------
A model asked to review its own prose is the same model that wrote it, so self-review
misses the same things every time, in the same direction. The only review that finds a
tell reliably is one that cannot be talked out of it. So every check here is mechanical:
count, match, compare. None of them has an opinion, and none of them can be persuaded.

THE RANGE COMES FROM THE CORPUS, NOT FROM A STYLE GUIDE
-------------------------------------------------------
Contraction density, comma-before-"and" rate and sentence cadence are not universal
virtues; they are one writer's fingerprint. An absolute threshold would push every
writer toward the same middle, which is the exact failure this layer exists to fix. So
`--measure` reads the register's own `corpus/` and writes the ranges into its
`voice.toml`, and the checks compare a draft against the writer, not against an ideal.
A register with no measured block gets a `not-measured` notice, never a silent pass.

WHAT IT DELIBERATELY DOES NOT CATCH
-----------------------------------
Meaning, accuracy, structure, whether the point is any good. Nothing here reads for
sense. The comma-splice test is a proxy (a comma followed by a fresh pronoun subject),
not a parser. Claims about price, stage or customers are not judged at all: this layer
is never the authority on them, so the check demands a `checked:` marker naming what a
human verified, which is the pattern to copy whenever a check cannot know the answer.

USAGE
-----
    check-voice.py <draft>...            lint drafts; the register is read from the path
    check-voice.py --list                the registered checks, one per line
    check-voice.py --self-test           every check fires on its positive sample
    check-voice.py --measure <register>  measure the corpus and print the block
    check-voice.py --measure <register> --write   ...and replace it in voice.toml
    check-voice.py --json                machine-readable findings

Exit: 0 no findings, 1 a finding, 2 it could not run (missing file, bad usage).
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from pathlib import Path

# ── the draft's own declaration ──────────────────────────────────────────────
# A draft may open with a small front-matter block. `medium` picks the platform limits;
# `checked` is the human's signature on the claims this layer cannot verify.
#   ---
#   medium: thread
#   checked: price, customers
#   ---
FRONT = re.compile(r"\A---\n(.*?)\n---\n", re.S)
FENCE = re.compile(r"```.*?```", re.S)
THREAD_SPLIT = re.compile(r"^---$", re.M)

EM_DASH = re.compile(r"[—―]")
CONTRACTION = re.compile(r"\b[A-Za-z]+['’](?:t|s|re|ve|ll|d|m)\b", re.I)
COMMA_AND = re.compile(r",\s+and\b", re.I)
# Proxy, not a parser: a comma followed by a fresh subject pronoun and more clause.
SPLICE = re.compile(r",\s+(?:i|you|he|she|it|we|they|that|this|there)\s+\w+", re.I)
FIRST_PERSON = re.compile(r"\b(?:i|we|my|our|me|us)\b", re.I)
SECOND_PERSON = re.compile(r"\b(?:you|your|yours)\b", re.I)
QUOTED = re.compile(r"\A[\"'“‘]")

# The default tell list. A register extends it: every backticked term under
# `## Never sound like` in its VOICE.md is added, so the never-list is enforced rather
# than merely read. That list is the one that does the work; it is also the easier of
# the two to write, because naming what you do not sound like is concrete.
AI_TELLS = [
    "leverage", "unlock", "empower", "delve", "seamless", "robust", "elevate",
    "harness", "tapestry", "testament", "realm", "paradigm", "synergy", "holistic",
    "cutting-edge", "game-changer", "supercharge", "streamline", "revolutionize",
    "transformative", "best-in-class", "world-class", "unparalleled",
    "in today's fast-paced", "it is important to note", "at the end of the day",
    "dive deep", "deep dive",
]
# A single-word tell is matched with its common inflections, because "unlocks" is the
# same tell as "unlock" and listing every ending is how a list goes stale.
def tell_pattern(term: str) -> str:
    core = re.escape(term)
    return rf"\b{core}(?:s|d|ed|ing|ly)?\b" if " " not in term else rf"\b{core}\b"

CLAIM_FAMILIES = {
    "price": [r"\$\s?\d", r"\bpricing\b", r"\bper month\b", r"\b/mo\b", r"\bper seat\b"],
    "stage": [r"\bbeta\b", r"\bearly access\b", r"\bgenerally available\b",
              r"\bwaitlist\b", r"\bv\d+\.\d+\b"],
    "customers": [r"\b\d[\d,]*\s+(?:users|customers|teams|companies|subscribers)\b",
                  r"\btrusted by\b", r"\bused by\b"],
}

DEFAULT_TARGET = {
    "medium": "post",
    "post_chars": 280,
    "thread_max_posts": 8,
    "short_sentence_words": 9,
    "long_sentence_words": 22,
    "splice_floor_words": 120,
}

# Every registered check, in report order. The self-test walks this list, so a check
# added without a positive and a negative sample fails the suite rather than shipping
# untested. `metric` checks print their number on every run, passing or not: slow drift
# is invisible to a check that only speaks on failure.
CHECKS: list[tuple[str, str]] = [
    ("em-dash", "an em-dash or horizontal bar, anywhere"),
    ("ai-tell-word", "a word from the tell list, plus the register's own never-list"),
    ("rhetorical-close", "the draft's last sentence is a question"),
    ("staccato-run", "three or more short sentences back to back, quotations exempt"),
    ("cadence-flat", "a short median with no sentence long enough to be a build"),
    ("no-comma-splice", "a long draft with zero comma splices did not come from a person"),
    ("contractions-low", "contraction density under the writer's own floor: reads assembled"),
    ("contractions-high", "contraction density over the writer's own ceiling: reads imitated"),
    ("comma-before-and", "comma-before-and rate outside the writer's own range (metric)"),
    ("person-balance", "an instructional draft whose subject is the writer (metric)"),
    ("post-too-long", "a post over the target platform's character limit"),
    ("thread-too-long", "a thread over the target platform's post limit"),
    ("unchecked-claim", "a price, stage or customer claim with no `checked:` marker"),
]


class Finding:
    def __init__(self, check: str, message: str, kind: str = "flag"):
        self.check, self.message, self.kind = check, message, kind

    def as_dict(self) -> dict:
        return {"check": self.check, "message": self.message, "kind": self.kind}


# ── a very small TOML reader, for voice.toml only ────────────────────────────
def load_toml(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    try:
        import tomllib
        return tomllib.loads(text)
    except ModuleNotFoundError:
        pass
    out: dict = {}
    cur = out
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        m = re.match(r"^\[(.+?)\]$", line)
        if m:
            cur = out.setdefault(m.group(1).strip(), {})
            continue
        m = re.match(r"^([A-Za-z0-9_.-]+)\s*=\s*(.+)$", line)
        if not m:
            continue
        key, val = m.group(1), m.group(2).strip()
        if val.startswith("["):
            cur[key] = [float(x) for x in re.findall(r"-?\d+(?:\.\d+)?", val)]
        elif val.startswith('"'):
            cur[key] = val.strip('"')
        elif val in ("true", "false"):
            cur[key] = val == "true"
        else:
            cur[key] = float(val) if "." in val else int(val)
    return out


# ── text handling ────────────────────────────────────────────────────────────
def front_matter(text: str) -> tuple[dict, str]:
    m = FRONT.match(text)
    if not m:
        return {}, text
    meta = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip().lower()] = v.strip()
    return meta, text[m.end():]


def prose(text: str) -> str:
    """Authored prose only: fenced blocks, headings and link targets are not voice."""
    text = FENCE.sub(" ", text)
    text = re.sub(r"^#{1,6} .*$", " ", text, flags=re.M)
    text = re.sub(r"\]\([^)]*\)", "]", text)
    text = re.sub(r"^\s*[-*+]\s+", "", text, flags=re.M)
    return text


def sentences(text: str) -> list[str]:
    """Terminal punctuation, or a blank line. Raw samples (replies especially) often end
    without a full stop, and treating a whole pull as one sentence wrecks every cadence
    measurement taken from it."""
    parts = re.split(r"(?<=[.!?])[ \t]*\n?[ \t]*|\n[ \t]*\n", text.strip())
    return [p.strip() for p in parts if p and p.strip()]


def words(text: str) -> list[str]:
    return re.findall(r"[A-Za-z'’-]+", text)


def per_1k(count: int, total_words: int) -> float:
    return round(1000.0 * count / total_words, 1) if total_words else 0.0


def never_list(register: Path | None) -> list[str]:
    """Backticked terms under `## Never sound like` in the register's VOICE.md."""
    if not register:
        return []
    voice = register / "VOICE.md"
    if not voice.is_file():
        return []
    text = voice.read_text(encoding="utf-8")
    m = re.search(r"^##+\s*Never sound like.*?$(.*?)(?=^##\s|\Z)", text, re.M | re.S)
    if not m:
        return []
    return [t.strip().lower() for t in re.findall(r"`([^`]+)`", m.group(1)) if t.strip()]


# ── the linter ───────────────────────────────────────────────────────────────
def lint(text: str, target: dict, measured: dict, tells: list[str]) -> list[Finding]:
    found: list[Finding] = []
    meta, body = front_matter(text)
    medium = meta.get("medium", target.get("medium", "post"))
    checked = {c.strip().lower() for c in meta.get("checked", "").split(",") if c.strip()}
    p = prose(body)
    sents = sentences(p)
    wds = words(p)
    n_words = len(wds)
    short_n = int(target["short_sentence_words"])
    long_n = int(target["long_sentence_words"])

    if EM_DASH.search(body):
        found.append(Finding("em-dash", f"{len(EM_DASH.findall(body))} em-dash or horizontal bar"))

    low = p.lower()
    hits = sorted({t for t in tells if re.search(tell_pattern(t), low)})
    if hits:
        found.append(Finding("ai-tell-word", "tell word: " + ", ".join(hits)))

    if sents and sents[-1].rstrip().endswith("?"):
        found.append(Finding("rhetorical-close", "the draft closes on a question"))

    run = 0
    for s in sents:
        is_short = len(words(s)) <= short_n and not QUOTED.match(s)
        run = run + 1 if is_short else 0
        if run >= 3:
            found.append(Finding("staccato-run", f"{run} short sentences back to back: \"{s[:48]}\""))
            run = 0

    lengths = [len(words(s)) for s in sents]
    if lengths:
        med = statistics.median(lengths)
        if med <= short_n and max(lengths) < long_n:
            found.append(Finding("cadence-flat",
                                 f"median {med:.0f} words, longest {max(lengths)}: all beats, no builds"))
    if n_words >= int(target["splice_floor_words"]) and not SPLICE.search(p):
        found.append(Finding("no-comma-splice",
                             f"{n_words} words and not one comma splice: nobody writes like that"))

    contractions = per_1k(len(CONTRACTION.findall(p)), n_words)
    comma_and = per_1k(len(COMMA_AND.findall(p)), n_words)
    found.append(Finding("comma-before-and", f"comma before \"and\": {comma_and}/1k words", "metric"))

    c_range = measured.get("contractions_per_1k")
    if not c_range:
        found.append(Finding("contractions-low",
                             "no measured range for this register: run --measure on its corpus", "notice"))
    else:
        if contractions < c_range[0]:
            found.append(Finding("contractions-low",
                                 f"contractions {contractions}/1k, under your floor {c_range[0]}: reads assembled"))
        if contractions > c_range[1]:
            found.append(Finding("contractions-high",
                                 f"contractions {contractions}/1k, over your ceiling {c_range[1]}"))
    a_range = measured.get("comma_and_per_1k")
    if a_range and not (a_range[0] <= comma_and <= a_range[1]):
        found.append(Finding("comma-before-and",
                             f"comma before \"and\" {comma_and}/1k is outside your range {a_range}"))

    first, second = len(FIRST_PERSON.findall(p)), len(SECOND_PERSON.findall(p))
    ratio = round(first / second, 2) if second else float(first)
    found.append(Finding("person-balance", f"first person to second person: {first}:{second}", "metric"))
    if meta.get("kind", "").lower() == "instructional" and first > second:
        found.append(Finding("person-balance",
                             f"an instructional draft whose subject is you, not the reader ({ratio}:1)"))

    if medium == "thread":
        posts = [x.strip() for x in THREAD_SPLIT.split(body) if x.strip()]
        if len(posts) > int(target["thread_max_posts"]):
            found.append(Finding("thread-too-long",
                                 f"{len(posts)} posts, limit {int(target['thread_max_posts'])}"))
        over = [i + 1 for i, x in enumerate(posts) if len(x) > int(target["post_chars"])]
        if over:
            found.append(Finding("post-too-long",
                                 f"post(s) {over} over {int(target['post_chars'])} characters"))
    elif medium == "post":
        if len(body.strip()) > int(target["post_chars"]):
            found.append(Finding("post-too-long",
                                 f"{len(body.strip())} characters, limit {int(target['post_chars'])}"))

    for family, patterns in CLAIM_FAMILIES.items():
        if family in checked:
            continue
        for pat in patterns:
            m = re.search(pat, body, re.I)
            if m:
                found.append(Finding("unchecked-claim",
                                     f"{family} claim \"{m.group(0)}\" with no `checked: {family}` marker"))
                break
    return found


# ── register plumbing ────────────────────────────────────────────────────────
def register_for(draft: Path) -> Path | None:
    """A draft at desks/<register>/outbox/<file> belongs to desks/<register>."""
    for parent in draft.resolve().parents:
        if (parent / "VOICE.md").is_file() or (parent / "voice.toml").is_file():
            return parent
    return None


def config_for(register: Path | None) -> tuple[dict, dict]:
    target = dict(DEFAULT_TARGET)
    measured: dict = {}
    if register and (register / "voice.toml").is_file():
        cfg = load_toml(register / "voice.toml")
        target.update({k: v for k, v in cfg.get("target", {}).items() if v not in (None, "")})
        measured = {k: v for k, v in cfg.get("measured", {}).items()
                    if isinstance(v, list) and len(v) == 2 and any(v)}
    return target, measured


def corpus_files(register: Path, source: str) -> list[Path]:
    root = register / source
    return sorted(p for p in root.rglob("*.md") if p.name != "README.md") if root.is_dir() else []


def measure(register: Path, source: str) -> dict:
    """The writer's own range, from their own unedited samples. Mean +/- one standard
    deviation across samples, so one atypical pull cannot move the floor on its own."""
    files = corpus_files(register, source)
    c_rates, a_rates, med_lens, total = [], [], [], 0
    for f in files:
        p = prose(front_matter(f.read_text(encoding="utf-8"))[1])
        n = len(words(p))
        if n < 20:
            continue
        total += n
        c_rates.append(per_1k(len(CONTRACTION.findall(p)), n))
        a_rates.append(per_1k(len(COMMA_AND.findall(p)), n))
        lens = [len(words(s)) for s in sentences(p)]
        if lens:
            med_lens.append(statistics.median(lens))
    if not c_rates:
        return {"source": source, "samples": 0, "words": 0}

    def band(vals: list[float]) -> list[float]:
        mid = statistics.mean(vals)
        spread = statistics.pstdev(vals) if len(vals) > 1 else max(1.0, mid * 0.25)
        return [round(max(0.0, mid - spread), 1), round(mid + spread, 1)]

    return {
        "source": source, "samples": len(c_rates), "words": total,
        "contractions_per_1k": band(c_rates), "comma_and_per_1k": band(a_rates),
        "median_sentence_words": round(statistics.median(med_lens)) if med_lens else 0,
    }


def measured_block(m: dict) -> str:
    lines = ["[measured]",
             "# GENERATED by: scripts/check-voice.py --measure <register> --write",
             "# Do not hand-edit. A stale corpus is re-pulled, never cleaned up.",
             f'source = "{m["source"]}"',
             f"samples = {m['samples']}",
             f"words = {m['words']}"]
    for key in ("contractions_per_1k", "comma_and_per_1k"):
        if key in m:
            lines.append(f"{key} = [{m[key][0]}, {m[key][1]}]")
    if "median_sentence_words" in m:
        lines.append(f"median_sentence_words = {m['median_sentence_words']}")
    return "\n".join(lines) + "\n"


def write_measured(register: Path, block: str) -> None:
    path = register / "voice.toml"
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    # Only a real section header counts. Partitioning on the bare string once matched
    # "[measured]" inside the file's own explanatory comment and ate the header with it.
    start = re.search(r"^\[measured\][ \t]*$", text, re.M)
    if start:
        rest = text[start.end():]
        nxt = re.search(r"^\[", rest, re.M)
        tail = rest[nxt.start():] if nxt else ""
        text = text[:start.start()] + block + ("\n" + tail if tail else "")
    else:
        text = (text.rstrip() + "\n\n" if text.strip() else "") + block
    path.write_text(text, encoding="utf-8")


# ── self-test ────────────────────────────────────────────────────────────────
SELF_TARGET = dict(DEFAULT_TARGET, post_chars=120, thread_max_posts=2, splice_floor_words=40)
SELF_MEASURED = {"contractions_per_1k": [10.0, 40.0], "comma_and_per_1k": [0.0, 8.0]}
# (check id, a draft that MUST fire it, a draft that must NOT)
SAMPLES: dict[str, tuple[str, str]] = {
    "em-dash": ("It works—mostly.", "It works, mostly."),
    "ai-tell-word": ("We leverage the data.", "We use the data."),
    "rhetorical-close": ("It shipped. Isn't that something?", "It shipped. That's the whole thing."),
    "staccato-run": ("It shipped. It works. It's fast.",
                     "It shipped this morning and it works, which is the part I did not expect."),
    "cadence-flat": ("It shipped. It works.",
                     "It shipped this morning and it works, which is the part I did not expect at all."),
    "no-comma-splice": (" ".join(["the build runs green on every push to the branch today"] * 6),
                        "I pushed it, it went green. " + " ".join(["a longer clause about the build"] * 9)),
    "contractions-low": ("I am not sure that is the thing we want to do here at all today.",
                         "I'm not sure that's the thing we'd do here, it's a bit much isn't it."),
    "contractions-high": ("I'm not sure that's it, I'd say it isn't, you're right, we've done.",
                          "I'm not sure that is the one we want here on this particular day, and "
                          "the reason is simple enough that it does not need a long explanation "
                          "from me about any of it right now."),
    "comma-before-and": ("I shipped it, and I tested it, and I pushed it, and I am done ok.",
                         "I shipped it and tested it and pushed it and then I stopped for the day."),
    "person-balance": ("---\nkind: instructional\n---\nI ran it. I checked it. You wait.",
                       "---\nkind: instructional\n---\nYou run it. You check your output. I wait."),
    "post-too-long": ("x " * 90, "short enough"),
    "thread-too-long": ("---\nmedium: thread\n---\none\n---\ntwo\n---\nthree",
                        "---\nmedium: thread\n---\none\n---\ntwo"),
    "unchecked-claim": ("It is $9 a month.", "---\nchecked: price\n---\nIt is $9 a month."),
}


def self_test() -> int:
    fails = 0
    registered = [c for c, _ in CHECKS]
    missing = [c for c in registered if c not in SAMPLES]
    if missing:
        print(f"  FAIL  registered checks with no sample: {missing}")
        fails += len(missing)
    for check in registered:
        if check not in SAMPLES:
            continue
        positive, negative = SAMPLES[check]
        fired = {f.check for f in lint(positive, SELF_TARGET, SELF_MEASURED, AI_TELLS) if f.kind == "flag"}
        quiet = {f.check for f in lint(negative, SELF_TARGET, SELF_MEASURED, AI_TELLS) if f.kind == "flag"}
        ok_fire, ok_quiet = check in fired, check not in quiet
        if not ok_fire:
            print(f"  FAIL  {check}: did not fire on its positive sample")
        if not ok_quiet:
            print(f"  FAIL  {check}: fired on its negative sample (a check that cries wolf gets bypassed)")
        fails += (not ok_fire) + (not ok_quiet)
        if ok_fire and ok_quiet:
            print(f"  ok    {check}")
    print(f"\ncheck-voice self-test: {len(registered)} checks, {fails} failure(s)")
    return 1 if fails else 0


# ── cli ──────────────────────────────────────────────────────────────────────
def main() -> int:
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("paths", nargs="*")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--measure", metavar="REGISTER")
    ap.add_argument("--check-measured", metavar="REGISTER",
                    help="exit 1 if the stored [measured] block no longer matches the corpus")
    ap.add_argument("--source", default="", help="corpus subdir to measure (default: the register's own)")
    ap.add_argument("--write", action="store_true", help="with --measure, replace [measured] in voice.toml")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.list:
        for check, why in CHECKS:
            print(f"{check:<20} {why}")
        return 0

    if args.self_test:
        return self_test()

    if args.check_measured:
        register = Path(args.check_measured)
        if not (register / "voice.toml").is_file():
            print(f"{register} has no voice.toml: nothing to check", file=sys.stderr)
            return 2
        target, stored = config_for(register)
        fresh = measure(register, str(target.get("corpus", "corpus/typed")))
        if not fresh["samples"]:
            print(f"{register}: corpus is empty, so the thresholds came from nowhere", file=sys.stderr)
            return 2
        drift = [k for k in ("contractions_per_1k", "comma_and_per_1k")
                 if stored.get(k) != fresh.get(k)]
        if drift:
            print(f"{register}: {', '.join(drift)} no longer matches the corpus; "
                  f"re-run --measure {register} --write")
            return 1
        print(f"{register}: measured block still matches its corpus "
              f"({fresh['samples']} samples, {fresh['words']} words)")
        return 0

    if args.measure:
        register = Path(args.measure)
        if not register.is_dir():
            print(f"not a register directory: {register}", file=sys.stderr)
            return 2
        target, _ = config_for(register)
        source = args.source or str(target.get("corpus", "corpus/typed"))
        m = measure(register, source)
        if not m["samples"]:
            print(f"no corpus samples under {register}/{source}: pull some before measuring",
                  file=sys.stderr)
            return 2
        block = measured_block(m)
        if args.write:
            write_measured(register, block)
            print(f"wrote [measured] into {register}/voice.toml ({m['samples']} samples, {m['words']} words)")
        else:
            print(block, end="")
        return 0

    if not args.paths:
        ap.print_usage(sys.stderr)
        return 2

    report, worst = [], 0
    for raw in args.paths:
        path = Path(raw)
        if not path.is_file():
            print(f"cannot read {path}: the check did not run", file=sys.stderr)
            worst = max(worst, 2)
            continue
        register = register_for(path)
        target, measured = config_for(register)
        tells = AI_TELLS + never_list(register)
        findings = lint(path.read_text(encoding="utf-8"), target, measured, tells)
        report.append({"file": str(path), "register": str(register) if register else None,
                       "findings": [f.as_dict() for f in findings]})
        if any(f.kind == "flag" for f in findings):
            worst = max(worst, 1)

    if args.json:
        print(json.dumps(report, indent=2))
        return worst

    for entry in report:
        print(f"{entry['file']}  ({entry['register'] or 'no register: defaults only'})")
        for f in entry["findings"]:
            mark = {"flag": "FLAG  ", "metric": "metric", "notice": "notice"}[f["kind"]]
            print(f"  {mark}  {f['check']:<18} {f['message']}")
        if not any(f["kind"] == "flag" for f in entry["findings"]):
            print("  clean   no tell fired")
    return worst


if __name__ == "__main__":
    raise SystemExit(main())
