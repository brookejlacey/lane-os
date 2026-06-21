# Lane OS

**A multi-session operating system for [Claude Code](https://docs.claude.com/en/docs/claude-code/overview): parallel, single-topic lanes over a shared, persistent context spine.**

Lane OS is a repository layout plus a small set of hooks, skills, and conventions that let you run many AI coding sessions at once without them stepping on each other, and without re-explaining your world at the start of every session.

It solves two problems that show up the moment you take agentic coding seriously:

1. **Parallel sessions clobber shared state.** If three sessions all try to update the same "what am I working on" files, they conflict on git and the whole thing collapses into merge hell.
2. **Every new session starts amnesiac.** Without a durable context layer, you paste the same background into chat over and over, and the agent still guesses.

Lane OS fixes both with one idea: **one window = one topic**, and every window may only write to the lane it owns.

---

## The core idea

You run work in **lanes**. A lane is one window (one session) scoped to one topic. There are three kinds:

| Lane type | What it is | Where it writes |
|---|---|---|
| **Code lane** | A product/code repository | Its own repo, plus a small status mirror in the spine |
| **Topic desk** | An ongoing non-code subject (finances, planning, research) | `desks/<topic>/` only |
| **The spine** | Your cross-cutting context (identity, priorities, memory) | `brain/`, `memory/`, `global/`, `skills/` |

All three share one **spine repo**: a single git repository holding your context layer (`brain/`), your durable memory (`memory/`), your global rules (`global/`), your reusable skills (`skills/`), and a thin status mirror of every code lane (`projects/`).

The rule that makes parallelism safe is the **write-lane invariant**: a session may write only to the lane it owns. A code-lane session never edits the spine. A desk session never edits another desk. Only a spine session rebuilds the cross-cutting files. This is enforced two ways: a `SessionStart` hook that tells each session its lane and boundaries, and a `PreToolUse` guard that blocks out-of-lane writes at the keystroke.

See [`docs/write-lane-invariant.md`](docs/write-lane-invariant.md) for the full rule and why it is structural, not a preference.

---

## What you get

```
lane-os/
├── global/
│   ├── CLAUDE.md          # the constitution: behavioral rules loaded every session
│   └── REFERENCE.md       # read-on-demand setup + architecture notes
├── brain/                 # the context spine (state files, rebuilt by spine sessions)
│   ├── WHO_I_AM.md        # identity, season, working style
│   ├── ACTIVE_NOW.md      # what is live right now, ordered by category
│   ├── DECISIONS.md       # recent decisions + reasoning
│   ├── CONCERNS.md        # open loops and worries
│   ├── PEOPLE.md          # collaborators, relationships
│   ├── WEEKLY_LOG.md      # rolling 2-week log
│   └── drafts/            # the one path EVERY lane may write (staging for merge)
├── memory/                # durable facts, one file per fact, frontmatter-indexed
│   ├── MEMORY.md          # the index loaded each session
│   └── README.md          # frontmatter schema + conventions
├── projects/              # thin status mirror of each code lane
│   └── _TEMPLATE/         # STATUS.md + MEMORY.md to copy per code lane
├── desks/                 # topic desks
│   └── _TEMPLATE/         # CLAUDE.md + LOG.md to copy per desk
├── skills/                # lifecycle slash-commands (orient, catchup, today, spark, recall, ...)
├── hooks/
│   └── session-start.sh   # detects the lane, pulls, injects a read-directive
├── scripts/
│   ├── hooks/
│   │   └── block-cross-lane-write.py   # PreToolUse guard enforcing the invariant
│   ├── new-lane.sh        # scaffold a new code lane or desk
│   ├── build-switchboard.py            # cross-lane awareness cache
│   ├── install.sh         # one-time machine setup (symlinks, hook registration)
│   └── remote/            # always-on hosts: code from your phone, non-sandbox
└── switchboard/           # local, gitignored cache of what moved in other lanes
```

---

## Quickstart

```bash
# 1. Clone and rename to your liking (this becomes your private spine repo)
git clone https://github.com/<you>/lane-os.git ~/work/spine
cd ~/work/spine

# 2. Run the installer: symlinks global/CLAUDE.md into ~/.claude,
#    links skills, and registers the SessionStart + PreToolUse hooks.
bash scripts/install.sh

# 3. Fill in your spine. These are templates; make them yours.
$EDITOR brain/WHO_I_AM.md brain/ACTIVE_NOW.md

# 4. Open a session here (the spine / workspace-root session) and try:
#    /orient    -> your daily sit-down
#    /spark     -> capture an idea from any lane without losing focus
```

To start a **code lane**, point a session at any code repo on your machine and add a `projects/<repo-name>/` folder in the spine (copy `projects/_TEMPLATE/`). To start a **desk**, copy `desks/_TEMPLATE/` to `desks/<topic>/`. The `scripts/new-lane.sh` helper does both.

---

## Code from anywhere, without a sandbox

Once your lanes exist, you can drive **real, full-filesystem sessions from your phone or any laptop**, against your actual repos with your real secrets and tools, by keeping a few always-on `claude remote-control` sessions on one machine you leave on. One host per lane means each one boots already scoped to the right context and write boundary. This is the opposite of the in-app sandbox (single repo, no secrets, pull-request only). See [`docs/code-from-anywhere.md`](docs/code-from-anywhere.md) and [`scripts/remote/`](scripts/remote/).

---

## Why a spine instead of one giant CLAUDE.md

A single ever-growing instruction file gets loaded in full on every session, gets expensive, and still does not hold the state that actually changes day to day. Lane OS splits the two:

- **Rules that rarely change** live in `global/CLAUDE.md` (the constitution) and load every session.
- **State that changes constantly** lives in `brain/` and `memory/`, and is *read on demand* via a compact pointer the hook injects, never pasted wholesale.

This keeps the always-loaded payload small while giving every session reliable access to the full, current picture. See [`docs/session-lifecycle.md`](docs/session-lifecycle.md).

---

## Documentation

- [`docs/philosophy.md`](docs/philosophy.md) - one window = one topic, and why
- [`docs/architecture.md`](docs/architecture.md) - the three lane types and the spine in detail
- [`docs/write-lane-invariant.md`](docs/write-lane-invariant.md) - the safety rule that makes parallelism work
- [`docs/session-lifecycle.md`](docs/session-lifecycle.md) - the SessionStart hook, restart vs refresh
- [`docs/memory.md`](docs/memory.md) - the durable-facts memory system
- [`docs/multi-machine.md`](docs/multi-machine.md) - symlinks, sync, working across machines
- [`docs/code-from-anywhere.md`](docs/code-from-anywhere.md) - drive real, non-sandbox sessions from your phone or any laptop
- [`docs/getting-started.md`](docs/getting-started.md) - adopt it step by step

- [`llms.txt`](llms.txt) - documentation map for pointing an AI agent at the repo in one paste (with `llms-full.txt`, the whole doc set concatenated into one fetchable file)

---

## Status

Lane OS is a scaffold, not a framework. There is nothing to install as a dependency and nothing to import. You clone it, make it yours, and the conventions do the work. Fork it, gut it, rename everything. The value is the shape, not the code.

## License

MIT. See [`LICENSE`](LICENSE).
