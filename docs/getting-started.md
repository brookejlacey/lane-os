# Getting started

## 1. Clone the spine

```bash
git clone https://github.com/<you>/lane-os.git ~/work/spine
cd ~/work/spine
```

In a real deployment you would fork this to a PRIVATE repo first, since your spine
fills up with personal context. This public repo is the generic template.

## 2. Install

```bash
bash scripts/install.sh
```

This symlinks the constitution and hook into `~/.claude`, links the skills, and
registers the SessionStart and PreToolUse hooks in `~/.claude/settings.json`. Restart
Claude Code afterward so the hooks load.

Optionally add `export LANE_OS_ROOT="$HOME/work/spine"` to your shell profile.

## 3. Make the spine yours

Fill in the templates. Start with the two that matter most:

- `brain/WHO_I_AM.md` - who you are and how you want the agent to work.
- `brain/ACTIVE_NOW.md` - what is live right now.

Then trim `global/CLAUDE.md` to your actual rules and delete the placeholder lines.

## 4. Add your first code lane

Pick a real code repo and register a mirror for it:

```bash
scripts/new-lane.sh code my-app
```

Now open a Claude Code session inside `my-app`. The hook will recognize it as a code
lane, inject its STATUS, and scope its writes. Try editing a brain file from there:
the guard will block it. That block is the system working.

## 5. Add a desk

```bash
scripts/new-lane.sh desk planning
```

Fill `desks/planning/CLAUDE.md` with that desk's posture, then open a session there.

## 6. Use the lifecycle

- `/orient` when you sit down.
- `/spark` to capture an idea from any lane without losing focus.
- `/catchup` to re-sync a session after another window pushed changes.
- `/spin-lane` to graduate an idea into a real lane.

That is the whole loop: orient, work in lanes, capture, merge from the spine, repeat.
