# Lane OS

**A multi-session operating system for [Claude Code](https://docs.claude.com/en/docs/claude-code/overview): parallel, single-topic lanes over a shared, persistent context spine, with the rules that govern it enforced by hooks and commit checks instead of remembered.**

Lane OS is a repository layout plus a small set of hooks, checks, skills and conventions that let you run many AI coding sessions at once without them stepping on each other, without re-explaining your world at the start of every session, and without the rules you gave the agent quietly decaying over months.

It solves three problems that show up the moment you take agentic coding seriously:

1. **Parallel sessions clobber shared state.** Three sessions updating the same "what am I working on" files conflict on git and the whole thing collapses into merge hell.
2. **Every new session starts amnesiac.** Without a durable context layer you paste the same background into chat over and over, and the agent still guesses.
3. **Rules held only in prose decay.** A preference you stated in June is gone by August, not because anyone deleted it, but because nothing checked it. Measured in the spine this came from: the two context files with a byte ceiling stayed flat over four months; the two governed only by a written brevity rule grew 2x and 5.2x.

One idea handles the first two: **one window = one topic**, and every window may only write to the lane it owns. One idea handles the third: **a rule either names the gate that enforces it, or it is recorded as judgment with the reason**, and the coverage ratio is measured from the file on every commit.

---

## What you get

Ordered by what is hardest to find elsewhere.

### 1. Concerns that declare how they close

`brain/CONCERNS.md` holds the open unknowns. Every item declares a **Probe** (a shell command the machine runs on a schedule, printing `CLOSED`, `OPEN` or `UNKNOWN`) or an **Owner** (the one human or lane who can close it, because no command can observe the closing event). `scripts/probe-concerns.py` runs the probes, stamps the results and sorts the file into READY TO CLOSE, DECISIONS OWED and OWNED WORK. A probe never closes an item on its own; it flags, a human confirms. A concern that declares neither fails the commit. [`docs/concerns.md`](docs/concerns.md)

### 2. A voice layer: distilled rules plus a raw corpus

Describe the voice you want and you get the average of everyone who ever claimed those
adjectives, which is the corporate-brochure register. So a **voice register** is a lane:
`VOICE.md` holds the distilled rules (a "sound like" list and a longer, more useful
"never sound like" list), and `corpus/` holds unedited real samples as dated pulls,
replies kept separately from posts and typed kept apart from spoken. Rules drift because
they are somebody's summary; the corpus does not. Every draft is read by
`scripts/check-voice.py` before a human sees it: thirteen mechanical checks whose
thresholds are measured from that writer's own corpus rather than from a style guide.
Check 16 proves the checks still fire; Check 17 runs them on the changed drafts.
[`docs/voice-layer.md`](docs/voice-layer.md)

### 3. The miss-to-rule-plus-check loop, with a gated-coverage ratchet

A found miss gets the instance fixed, the rule written with its scar attached, a gate wired when the signature is deterministic, and the rule bullet naming the gate. `/reflect implement` runs that loop from a session's learnings. The constitution opens with `Coverage today: N of M bullets are gated`; that number is measured by `scripts/find-decayed-rules.py`, rules with no deterministic signature are triaged in `global/rule-triage.tsv` with the reason, and Check 12 fails the commit when the claim and the file disagree. The decay surface is a list you work down, not a thing you rediscover one embarrassment at a time. [`docs/gated-rules.md`](docs/gated-rules.md), [`docs/miss-to-rule-loop.md`](docs/miss-to-rule-loop.md)

### 4. The write-lane invariant

A session may write only to the lane it owns plus the shared inbox `brain/drafts/`. A code lane writes its repo and its `projects/<name>/` mirror; a desk writes its `desks/<topic>/`; only a spine session rebuilds the cross-cutting files. A `PreToolUse` guard blocks out-of-lane writes at the keystroke, a SessionStart directive tells each session its boundary, and because a fail-open guard cannot report its own death, `scripts/test-lanes.sh` feeds it 25 representative writes on every commit and asserts it still blocks. [`docs/write-lane-invariant.md`](docs/write-lane-invariant.md)

### 5. Byte budgets on context files

Every file a session reads whole carries a budget in one table, `scripts/check-file-budgets.py`: hard ceilings for the four always-loaded files, warn-only for everything else, the four summed as their own row, and a code lane's own `CLAUDE.md`, `BACKLOG.md` and `DECISIONS.md` (above its `## Archive` divider) from the same table. Prune before you add; move history to an archive file verbatim. [`docs/context-budgets.md`](docs/context-budgets.md)

### 6. A synthesis layer above the codebase

`brain/` holds what no single repo can: who you are, what is live right now across every lane, the decisions and their reasoning, the open concerns, the people, a two-week log. Code lanes mirror a thin `STATUS.md` and `MEMORY.md` into `projects/`, and a spine session rebuilds the brain from those plus the drafts every lane may stage. `memory/` holds durable facts one per file. The switchboard shows what every other window is doing and what it is currently on, so a session asks the neighbouring lane instead of re-deriving its work. [`docs/architecture.md`](docs/architecture.md), [`docs/switchboard.md`](docs/switchboard.md)

### 7. Behavioural rules for the agent toward the human

The constitution carries rules for the reply, not only the code: a reply is ten lines or fewer, finished work is reported in a five-line envelope, a miss gets the corrected fact and no apology, nothing gets sized or clocked. The reply cap is gated by a pair of hooks: a Stop hook that only measures, and a UserPromptSubmit hook that instructs before the next reply once the log shows drift, so a well-behaved session pays nothing. The rest are recorded as judgment, honestly, with the reason no detector can exist. [`docs/agent-toward-human.md`](docs/agent-toward-human.md), [`docs/reply-length-gate.md`](docs/reply-length-gate.md)

### Also in the box

- **The session-start pointer hook.** Detects the lane from the working directory, pulls, and injects a compact read-directive naming the exact files to read, never their contents (hook stdout truncates; a dumped file is a silently half-read file). [`docs/session-lifecycle.md`](docs/session-lifecycle.md)
- **`audit-cheap.sh`**, seventeen sub-second drift checks wired into a pre-commit hook that judges only the staged set, so parallel sessions in one checkout do not fail each other's commits. [`docs/drift-checks.md`](docs/drift-checks.md)
- **The rules sync** that propagates the constitution into every code lane, defers the commit in a repo with a live session (writes are safe, the git index is not), and can never write into a repo published to an outside reader, because its deny list derives from the publisher's own audience table. **The shared-repo publisher** with per-audience allow and deny lists, a fail-closed content scrub, an allowlisted commit and a second lock installed in the target. [`docs/rules-sync-and-shared-repos.md`](docs/rules-sync-and-shared-repos.md)
- **`/preflight` and `/ship`**, the open and close of a build: five gates, a blind-spot pass, a bounded interview, a plan ordered by what will change, a deviation log the build writes into and the ship step folds into an honest Verified / Code-shipped / Inferred report.
- **Worktree guidance** for two sessions in one lane, and what a driven session does to your git index. [`docs/parallel-lanes-worktrees.md`](docs/parallel-lanes-worktrees.md)
- **Code from anywhere**: always-on remote-control sessions, one per lane, driven from a phone with the full filesystem. [`docs/code-from-anywhere.md`](docs/code-from-anywhere.md)

---

## The layout

```
lane-os/
├── global/
│   ├── CLAUDE.md              # the constitution, opens with its own gated-coverage count
│   ├── rule-triage.tsv        # rules that genuinely cannot be gated, with the reason
│   └── REFERENCE.md           # read-on-demand: hooks, checks, scripts, routing
├── brain/                     # the synthesis layer (state files, rebuilt by spine sessions)
│   ├── ACTIVE_NOW.md  CONCERNS.md  DECISIONS.md  PEOPLE.md  WEEKLY_LOG.md  WHO_I_AM.md
│   └── drafts/                # the one path EVERY lane may write
├── memory/                    # durable facts, one file per fact, indexed by MEMORY.md
├── projects/_TEMPLATE/        # STATUS.md + MEMORY.md mirror, one per code lane
├── desks/_TEMPLATE/           # CLAUDE.md + LOG.md, one per topic desk
├── desks/_TEMPLATE-voice/     # a voice register: VOICE.md + voice.toml + corpus/ + outbox/
├── skills/                    # orient, catchup, today, week, since, spark, spin-lane, recall,
│                              # reflect (+ implement mode), preflight, ship
├── hooks/session-start.sh     # detects the lane, pulls, injects the read-directive
├── scripts/
│   ├── hooks/
│   │   ├── block-cross-lane-write.py    # PreToolUse: the write-lane guard
│   │   ├── advisory-reply-length.py     # Stop: measures the reply, silent
│   │   ├── preflight-reply-length.py    # UserPromptSubmit: instructs on drift
│   │   └── shared-repo-pre-commit.sh    # the second lock inside a shared repo
│   ├── audit-cheap.sh         # 17 drift checks; the pre-commit gate runs it --staged
│   ├── check-voice.py         # the 13 voice checks; --measure reads the register's corpus
│   ├── find-decayed-rules.py  # gated / judgment / untriaged, the coverage ratchet
│   ├── probe-concerns.py      # runs every concern's Probe, stamps the result
│   ├── check-file-budgets.py  # the one budget table
│   ├── sync-rules.py          # constitution -> every code lane, live-session and shared-repo safe
│   ├── publish-shared-repo.py # a lane's cleared slice -> a repo an outside reader sees
│   ├── build-switchboard.py   # what every other lane is doing, and what it is on
│   ├── workspace_lib.py       # manifest, repo discovery, the derived deny list, live sessions
│   ├── install.sh  install-git-hooks.sh  new-lane.sh  lane-doctor.sh  build-llms-full.sh
│   ├── test-lanes.sh  tests-*.py  tests-*.sh     # every gate proves it blocks
│   └── remote/                # always-on hosts for code-from-anywhere
├── workspace.toml             # your workspace roots and code lanes
└── switchboard/               # local, gitignored: SWITCHBOARD.html + state.json
```

---

## Quickstart

```bash
# 1. Clone and rename to your liking (this becomes your private spine repo)
git clone https://github.com/<you>/lane-os.git ~/work/spine
cd ~/work/spine

# 2. Install: symlinks global/CLAUDE.md into ~/.claude, links skills, registers the
#    SessionStart, PreToolUse, Stop and UserPromptSubmit hooks, installs the commit gate.
bash scripts/install.sh

# 3. Fill in your spine. These are templates; make them yours.
$EDITOR brain/WHO_I_AM.md brain/ACTIVE_NOW.md brain/CONCERNS.md workspace.toml

# 4. Prove the gates are live, then open a spine session and try /orient.
bash scripts/audit-cheap.sh
```

To start a **code lane**, `scripts/new-lane.sh code <repo-name>` and open a session in that repo. To start a **desk**, `scripts/new-lane.sh desk <topic>`. After you edit the constitution, `python3 scripts/sync-rules.py` carries it into every code lane. [`docs/getting-started.md`](docs/getting-started.md)

---

## Why a spine instead of one giant CLAUDE.md

A single ever-growing instruction file loads in full on every session, gets expensive, and still does not hold the state that changes day to day. Lane OS splits the two: rules that rarely change live in `global/CLAUDE.md` and load every session, under a byte ceiling; state that changes constantly lives in `brain/` and `memory/` and is read on demand via a compact pointer the hook injects, never pasted wholesale. And because a rule that is merely loaded still decays, the ones with a deterministic signature are enforced by a hook or a check that names itself on the rule.

---

## Documentation

- [`docs/philosophy.md`](docs/philosophy.md), one window = one topic, and why
- [`docs/architecture.md`](docs/architecture.md), the three lane types and the spine
- [`docs/write-lane-invariant.md`](docs/write-lane-invariant.md), the safety rule that makes parallelism work
- [`docs/session-lifecycle.md`](docs/session-lifecycle.md), the SessionStart hook, restart vs refresh
- [`docs/gated-rules.md`](docs/gated-rules.md), gated or judgment, and the coverage ratchet
- [`docs/miss-to-rule-loop.md`](docs/miss-to-rule-loop.md), what a miss turns into
- [`docs/concerns.md`](docs/concerns.md), Probe or Owner
- [`docs/context-budgets.md`](docs/context-budgets.md), the one budget table
- [`docs/drift-checks.md`](docs/drift-checks.md), audit-cheap and the staged commit gate
- [`docs/reply-length-gate.md`](docs/reply-length-gate.md), measure after, instruct before
- [`docs/agent-toward-human.md`](docs/agent-toward-human.md), the behavioural rules
- [`docs/voice-layer.md`](docs/voice-layer.md), distilled rules plus a raw corpus, and the draft linter
- [`docs/switchboard.md`](docs/switchboard.md), what the other windows are doing
- [`docs/rules-sync-and-shared-repos.md`](docs/rules-sync-and-shared-repos.md), propagation, and repos an outside reader sees
- [`docs/parallel-lanes-worktrees.md`](docs/parallel-lanes-worktrees.md), two sessions in one lane
- [`docs/memory.md`](docs/memory.md), the durable-facts memory system
- [`docs/multi-machine.md`](docs/multi-machine.md), symlinks, sync, working across machines
- [`docs/code-from-anywhere.md`](docs/code-from-anywhere.md), real sessions from your phone
- [`docs/getting-started.md`](docs/getting-started.md), adopt it step by step
- [`llms.txt`](llms.txt), the documentation map for pointing an agent at this repo in one paste; [`llms-full.txt`](llms-full.txt) is the whole doc set in one fetchable file

---

## What lane-os does not do

Lane OS has no app-driving verification CLI and no feature map per product repo. `/ship` runs the gates a project already declares in its own `TESTING.md` and composes the verification skills your agent already has, but nothing here launches your app, walks its features and reports which ones still work. That is the complementary piece, and [pstack](https://github.com/poteto/pstack)'s verification skill is built exactly for it: one skill, one repo, a feature map the agent verifies against. Lane OS is the layer above the codebase; pair it with something like that inside each one.

## Status

Lane OS is a scaffold, not a framework. There is nothing to install as a dependency and nothing to import. You clone it, make it yours, and the conventions and the checks do the work. Fork it, gut it, rename everything. The value is the shape, and the fact that the shape is checked.

## License

MIT. See [`LICENSE`](LICENSE).
