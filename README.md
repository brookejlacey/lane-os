# Lane OS

**A home repo for [Claude Code](https://docs.claude.com/en/docs/claude-code/overview) that runs many windows at once. Each window is locked to its own lane by a hook and only the home window rebuilds the shared state. Code windows open in their own repo with the rules copied in.**

A home repo is the one repository every session starts from: who you are, what is live right now, the decisions and the rules. Lane OS is a home repo built for parallel work; it calls that repo the spine and the window opened at its root the spine session. The spine this scaffold came from runs about twenty lanes, each a window that knows exactly what it owns, with a hook that blocks any write outside it and a commit gate that proves the hook still blocks.

It solves three problems that show up the moment you run more than one session:

1. **Parallel sessions clobber shared state.** Three sessions updating the same "what am I working on" files conflict on git and the whole thing collapses into merge hell.
2. **Every new session starts amnesiac.** Without a durable context layer you paste the same background into chat over and over while the agent still guesses.
3. **Rules decay two ways.** A rule held only in prose quietly stops applying: in the spine this came from, the two context files with a byte ceiling stayed flat over four months while the two governed only by a written brevity rule grew 2x and 5.2x. The fix that looks obvious, turning every miss into a new always-loaded rule plus a check, fails the other way. It took that spine's always-loaded rules from 51 lines to 103 in four months. A longer instruction file lowers how well each line is followed.

One idea handles the first two: **one window = one topic**, and every window may only write to the lane it owns. One idea handles the third: **a rule loads only where it applies, as one line naming the file that holds its detail**. A correction is a note first, becomes a rule line when the same miss happens again and gets a gate only where the harm is outward or cannot be undone.

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

### 3. Rules that load where they apply, one line each

`global/CLAUDE.md` loads in every session on every lane, so it holds only what applies everywhere: one line per rule, each naming the memory file that holds its detail, exceptions and history. The rules only spine sessions need live in the spine's own `CLAUDE.md`. The rules only lanes need print in the SessionStart output, the one channel that reaches a code window. A voice register's rules live in its desk, a build's in `/preflight` and `/ship`. In the spine this came from, moving rules to where they apply took the always-loaded file from 103 rule lines to 72. A correction is a note first, becomes a loaded line only when the same miss happens a second time (`/recall` searches the session transcripts to find out) and gets a hook only where the harm is outward or cannot be undone. An earlier version of this repo ran a coverage ratchet that failed a commit when the share of gated rules dropped; it rewarded new rules, so it was retired, with every hook kept. [`docs/miss-to-rule-loop.md`](docs/miss-to-rule-loop.md), [`docs/gated-rules.md`](docs/gated-rules.md)

### 4. The write-lane invariant

A session may write only to the lane it owns plus the shared inbox `brain/drafts/`. A code lane writes its repo and its `projects/<name>/` mirror; a desk writes its `desks/<topic>/`; only a spine session rebuilds the cross-cutting files. A `PreToolUse` guard blocks out-of-lane writes at the keystroke, a SessionStart directive tells each session its boundary, and because a fail-open guard cannot report its own death, `scripts/test-lanes.sh` feeds it 25 representative writes on every commit and asserts it still blocks. [`docs/write-lane-invariant.md`](docs/write-lane-invariant.md)

### 5. Byte budgets on context files

Every file a session reads whole carries a budget in one table, `scripts/check-file-budgets.py`: hard ceilings for the four always-loaded files, warn-only for everything else, the four summed as their own row, and a code lane's own `CLAUDE.md`, `BACKLOG.md` and `DECISIONS.md` (above its `## Archive` divider) from the same table. Prune before you add; move history to an archive file verbatim. [`docs/context-budgets.md`](docs/context-budgets.md)

### 6. A synthesis layer above the codebase

`brain/` holds what no single repo can: who you are, what is live right now across every lane, the decisions and their reasoning, the open concerns, the people, a two-week log. Code lanes mirror a thin `STATUS.md` and `MEMORY.md` into `projects/`, and a spine session rebuilds the brain from those plus the drafts every lane may stage. `memory/` holds durable facts one per file. The switchboard shows what every other window is doing and what it is currently on, so a session asks the neighbouring lane instead of re-deriving its work. [`docs/architecture.md`](docs/architecture.md), [`docs/switchboard.md`](docs/switchboard.md)

### 7. Behavioural rules for the agent toward the human

The constitution carries rules for the reply, not only the code: a reply is ten lines or fewer, finished work is reported in a five-line envelope, a miss gets the corrected fact and no apology, nothing gets sized or clocked. The reply cap is gated by a pair of hooks: a Stop hook that only measures, and a UserPromptSubmit hook that instructs before the next reply once the log shows drift, so a well-behaved session pays nothing. The rest are judgment, because no check can see a reply; each is one line naming its memory file. [`docs/agent-toward-human.md`](docs/agent-toward-human.md), [`docs/reply-length-gate.md`](docs/reply-length-gate.md)

### Also in the box

- **The session-start pointer hook.** Detects the lane from the working directory, pulls, and injects a compact read-directive naming the exact files to read, never their contents (hook stdout truncates; a dumped file is a silently half-read file). [`docs/session-lifecycle.md`](docs/session-lifecycle.md)
- **`audit-cheap.sh`**, sixteen sub-second drift checks wired into a pre-commit hook that judges only the staged set, so parallel sessions in one checkout do not fail each other's commits. [`docs/drift-checks.md`](docs/drift-checks.md)
- **The rules sync** that propagates the constitution into every code lane on its own after an edit (a PostToolUse hook), defers the commit in a repo with a live session (writes are safe, the git index is not), and can never write into a repo published to an outside reader, because its deny list derives from the publisher's own audience table. **The shared-repo publisher** with per-audience allow and deny lists, a fail-closed content scrub, an allowlisted commit and a second lock installed in the target. [`docs/rules-sync-and-shared-repos.md`](docs/rules-sync-and-shared-repos.md)
- **`/preflight` and `/ship`**, the open and close of a build: five gates, a blind-spot pass, a bounded interview, a plan ordered by what will change, a deviation log the build writes into and the ship step folds into an honest Verified / Code-shipped / Inferred report.
- **Worktree guidance** for two sessions in one lane, and what a driven session does to your git index. [`docs/parallel-lanes-worktrees.md`](docs/parallel-lanes-worktrees.md)
- **Code from anywhere**: always-on remote-control sessions, one per lane, driven from a phone with the full filesystem. [`docs/code-from-anywhere.md`](docs/code-from-anywhere.md)

---

## The layout

```
lane-os/
├── CLAUDE.md                  # the rules for sessions inside the spine (spine upkeep, the brain)
├── global/
│   ├── CLAUDE.md              # the rules for every session, one line each, each naming its file
│   └── REFERENCE.md           # read-on-demand: hooks, checks, scripts, routing
├── brain/                     # the synthesis layer (state files, rebuilt by spine sessions)
│   ├── ACTIVE_NOW.md  CONCERNS.md  DECISIONS.md  PEOPLE.md  WEEKLY_LOG.md  WHO_I_AM.md
│   └── drafts/                # the one path EVERY lane may write
├── memory/                    # durable facts, one per file: the rule files, plus MEMORY.md for the rest
├── projects/_TEMPLATE/        # STATUS.md + MEMORY.md mirror, one per code lane
├── desks/_TEMPLATE/           # CLAUDE.md + LOG.md, one per topic desk
├── desks/_TEMPLATE-voice/     # a voice register: VOICE.md + voice.toml + corpus/ + outbox/
├── skills/                    # catchup, since, spark, spin-lane, recall, reflect
│                              # (+ implement mode), preflight, ship
├── hooks/session-start.sh     # detects the lane, pulls, prints the lane rules and the read-directive
├── scripts/
│   ├── hooks/
│   │   ├── block-cross-lane-write.py    # PreToolUse: the write-lane guard
│   │   ├── advisory-reply-length.py     # Stop: measures the reply, silent
│   │   ├── preflight-reply-length.py    # UserPromptSubmit: instructs on drift
│   │   ├── sync-rules-on-edit.sh        # PostToolUse: the rules sync after an edit to the rules
│   │   └── shared-repo-pre-commit.sh    # the second lock inside a shared repo
│   ├── audit-cheap.sh         # 16 drift checks; the pre-commit gate runs it --staged
│   ├── check-voice.py         # the 13 voice checks; --measure reads the register's corpus
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

# 4. Prove the gates are live, then open a spine session and run /catchup.
bash scripts/audit-cheap.sh
```

To start a **code lane**, `scripts/new-lane.sh code <repo-name>` and open a session in that repo. To start a **desk**, `scripts/new-lane.sh desk <topic>`. An edit to `global/CLAUDE.md` starts `scripts/sync-rules.py` on its own, which carries the rules into every code lane. [`docs/getting-started.md`](docs/getting-started.md)

---

## Why a spine instead of one giant CLAUDE.md

A single ever-growing instruction file loads in full on every session, gets expensive, and still does not hold the state that changes day to day. Lane OS splits three things apart. Rules load only where they apply, one line each, under a byte ceiling. Their detail lives in memory files a session opens when a rule meets an edge case. State that changes constantly lives in `brain/` and is read on demand via a compact pointer the hook injects, never pasted wholesale. A rule whose harm is outward or cannot be undone is also enforced by a hook or a check that its line names.

---

## Documentation

- [`docs/philosophy.md`](docs/philosophy.md), one window = one topic, and why
- [`docs/architecture.md`](docs/architecture.md), the three lane types and the spine
- [`docs/write-lane-invariant.md`](docs/write-lane-invariant.md), the safety rule that makes parallelism work
- [`docs/session-lifecycle.md`](docs/session-lifecycle.md), the SessionStart hook, restart vs refresh
- [`docs/gated-rules.md`](docs/gated-rules.md), gated or judgment, when a gate earns its place, the retired ratchet
- [`docs/miss-to-rule-loop.md`](docs/miss-to-rule-loop.md), a note first, a rule on the second miss, where each rule's line loads
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

**A new machine cannot rebuild itself from the spine.** `workspace.toml` names each code lane but not its clone address, so the spine knows which repos exist on this machine without being able to clone them onto another one.

**The spine this came from runs more than is shipped here.** Each of these depends on the machines and services it runs on, so each is described rather than included:

- A prompt-time hook that loads a pack of rules when the prompt's own words call for it, so a rule can load by topic as well as by folder.
- A parser for shell commands, so the write-lane guard also sees a write made through Bash. The guard here sees Write, Edit, MultiEdit and NotebookEdit.
- A full-text index over memory and every session transcript on every machine, with a nightly pass that applies queued memory edits without a model.
- An always-on machine that runs the scheduled jobs and headless handoffs from clones no interactive session uses.
- A queue for failures an agent can fix, so they wait for the next spine session instead of reaching the human.
- A gate on payments, signatures and making a repo public: each stops unless the human's own last message names it. An unattended run never gets that exception.

## Status

Lane OS is a scaffold, not a framework. There is nothing to install as a dependency and nothing to import. You clone it, make it yours, and the conventions and the checks do the work. Fork it, gut it, rename everything. The value is the shape, and the fact that the shape is checked.

## License

MIT. See [`LICENSE`](LICENSE).
