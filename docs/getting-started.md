# Getting started

## 1. Clone it as your spine

```bash
git clone https://github.com/<you>/lane-os.git ~/work/spine
cd ~/work/spine
```

Rename the folder to anything. Make the repo private: your real spine holds your
context. The hooks look for the spine at a few common paths and honor `LANE_OS_ROOT`.

## 2. Install

```bash
bash scripts/install.sh
```

Symlinks `global/CLAUDE.md` into `~/.claude`, links the skills, registers the
SessionStart, PreToolUse, Stop and UserPromptSubmit hooks in `~/.claude/settings.json`,
and installs the pre-commit gate in the spine. Restart Claude Code afterward so the hooks
load.

Optionally add to your shell profile:

```bash
export LANE_OS_ROOT="$HOME/work/spine"
export LANE_OS_WORKSPACE_ROOTS="$HOME/repos:$HOME/work"   # where your code repos live
```

## 3. Make the spine yours

Fill in the templates. Start with the ones that matter most:

- `brain/WHO_I_AM.md`: who you are and how you want the agent to work.
- `brain/ACTIVE_NOW.md`: what is live right now.
- `brain/CONCERNS.md`: the open unknowns, each with a `**Probe:**` or an `**Owner:**`.
- `workspace.toml`: your workspace roots and the code repos that receive the rules.

Then trim `global/CLAUDE.md` to your actual rules. Every `- ` bullet in it is a rule:
either name the hook or check that enforces it, or add a row to
`global/rule-triage.tsv` saying why none can. Restate the `Coverage today` line from
`python3 scripts/find-decayed-rules.py --count`; Check 12 will hold you to it.

## 4. Prove the gates are live

```bash
bash scripts/audit-cheap.sh
```

Seventeen checks, about a second. The interesting ones on day one: Check 9 (the write-lane
guard blocks, 25 cases), Check 12 (the coverage line matches the file), Check 8 (every
concern declares how it closes), Check 4 (every state file is inside its budget).

## 5. Add your first code lane

```bash
scripts/new-lane.sh code my-app        # creates projects/my-app/ from the template
python3 scripts/sync-rules.py my-app   # writes the constitution into the repo
```

Add a `[[repos]]` entry for `my-app` in `workspace.toml` so future syncs reach it. Now
open a Claude Code session inside `my-app`. The hook recognizes it as a code lane,
points it at its STATUS and MEMORY, and scopes its writes. Try editing a brain file from
there: the guard blocks it. That block is the system working.

## 6. Add a desk

```bash
scripts/new-lane.sh desk research
```

Fill that desk's `CLAUDE.md` with its posture, then open a session there.

## 7. Add a voice register

```bash
scripts/new-lane.sh voice writing
```

Fill that register's `VOICE.md` with a "sound like" list and a longer "never sound like"
list, then pull raw samples of your own writing into its `corpus/typed/` and
`corpus/spoken/` and measure them:

```bash
python3 scripts/check-voice.py --measure desks/writing --write
```

The linter's thresholds now come from your own samples rather than from a style guide.
Drop a draft in that register's `outbox/` and run `python3 scripts/check-voice.py` on it.
[`docs/voice-layer.md`](voice-layer.md)

## 8. Use the lifecycle

- `/orient` when you sit down (spine session).
- `/spark` to capture an idea from any lane without losing focus.
- `/catchup` to re-sync a session after another window pushed changes; it merges drafts
  and runs the concern probes.
- `/preflight` before a non-trivial build; `/ship` when it is done.
- `/reflect implement` when a session taught you something: it lands the learning as a
  gate, not a note.
- `/spin-lane` to graduate an idea into a real lane.

## 9. Keep it honest

- After any edit to `global/CLAUDE.md`: `python3 scripts/sync-rules.py`.
- On a machine that stays on, schedule `scripts/probe-concerns.py`,
  `scripts/check-file-budgets.py --over-only` and `scripts/build-switchboard.py`.
- When you publish a lane's docs to someone outside your workspace, add them as an
  audience in `scripts/publish-shared-repo.py` and publish through it. The sync denies
  that repo from that moment.

That is the whole loop: orient, work in lanes, capture, merge from the spine, and let
the checks catch what you forgot.
