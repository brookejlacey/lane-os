# Working across machines

Lane OS is git-native, so multiple machines stay in sync by pulling the spine.

## The symlink architecture

On each machine, a few symlinks point the agent's config at the spine repo so edits
land in one place with no drift:

- `~/.claude/CLAUDE.md` -> `<spine>/global/CLAUDE.md`
- `~/.claude/hooks/session-start.sh` -> `<spine>/hooks/session-start.sh`
- `~/.claude/skills/<name>` -> `<spine>/skills/<name>` (kept current by the hook)

`scripts/install.sh` sets these up. Keep them as symlinks, never copies. A stale copy
is the classic cause of "I edited the hook but nothing changed": the registered path
was a copy, so your edit never ran.

## Sync

`git pull` the spine and you have the latest brain, statuses, config, and skills. Code
repos sync through their own remotes. Nothing needs dual-writing once the symlinks are
in place.

If a push is rejected, `git pull --rebase` and retry. On a real merge conflict in the
spine, surface it rather than resolving blind, because the brain files are meant to be
coherent across each other.

## Different paths on different machines

The hook and guard locate the spine via `LANE_OS_ROOT` first, then a list of common
locations. If your spine lives somewhere unusual on a given machine, set
`LANE_OS_ROOT` in that machine's shell profile and everything else follows.

## Remote / always-on hosts

You can run always-on sessions on a home server or remote host (for example, to drive
from a phone). Each lane you want reachable becomes its own long-running session rooted
in that lane's directory, so it boots with the right context and write boundary. The
same hook and guard apply unchanged.
