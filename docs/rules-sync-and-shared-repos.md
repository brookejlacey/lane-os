# Rules sync, and repos an outside reader sees

Two scripts, one manifest, and two safety properties that each failed as prose before
they were code.

## The manifest: `workspace.toml`

Names your workspace roots (where code repos live), the paths the sync writes inside
each lane, and the repos that receive the rules. A repo not listed is still picked up
when it already carries a generated copy, so a lane you bootstrapped by hand keeps
syncing.

## The sync: `scripts/sync-rules.py`

A rule that lives in one repo is not a rule. After any edit to `global/CLAUDE.md`:

```bash
python3 scripts/sync-rules.py            # write, commit, push in every target
python3 scripts/sync-rules.py --dry-run
python3 scripts/sync-rules.py alpha      # one repo (an operator override)
```

Per target it writes `.claude/global-rules.md` (a generated copy with a header saying
so), makes sure the lane's `CLAUDE.md` imports it with `@.claude/global-rules.md` (so
the lane's own mechanism notes stay), and keeps a marked block current in `AGENTS.md`
for agents that read that instead.

**Property 1: it never touches the git index of a repo with a session open.** It still
writes the files, which is safe because they are generated and never hand-edited in a
lane, and the lane's next commit carries them. It defers only `git add` and
`git commit`, reporting `deferred: session open`. Skipping the repo outright is not a
deferral: a lane with a long-lived session then never syncs and works to rules the rest
of the workspace has replaced. Liveness is decided by `~/.claude/sessions/<pid>.json`
plus `os.kill(pid, 0)`, not file age. A `deferred` row is not a failure and needs no
follow-up.

**Property 2: it never writes into a repo published to an outside reader.** See below.

A rejected push gets up to three rebase-and-retry rounds (generated state rebases
safely); a conflict aborts and is reported, never resolved blind. A `commit failed` row
means a repo-side gate refused it: read that before re-running anything.

## The publisher: `scripts/publish-shared-repo.py`

A collaborator or partner reads a repo through their own agent. They never see your
spine. The publisher produces the repo they read, from one lane, under three rules:

1. **Allowlist the paths, deny-list the rest.** Named folders of one lane publish whole.
   Nothing outside the lane is reachable, because the lane path is the root of the walk.
2. **Fail closed on content.** Every byte about to be written is scanned against the
   deny patterns (credentials, an `INTERNAL ONLY` marker, paths into the private spine,
   banking identifiers, plus per-audience patterns). One hit aborts the whole publish
   and writes nothing, naming the file, the line and the reason. Fix the source or deny
   the file; never loosen a pattern to get past it.
3. **Only this script commits there, and only what it wrote.** It resets the target to
   origin before writing (every file is derived, so two hosts publishing produce
   identical competing commits; rebasing them is work with no answer), stages an
   allowlist rather than `git add -A`, and refuses to commit if any file it did not write
   is present. It installs `scripts/hooks/shared-repo-pre-commit.sh` into the target as
   a second lock, which refuses any staged file outside the published manifest. `inbox/`
   is the reader's, and flows the other way.

After the push it confirms against origin, not against its own exit code: a publisher
that cannot see its own output is not finished.

```bash
python3 scripts/publish-shared-repo.py example-partner-docs --dry-run
python3 scripts/publish-shared-repo.py example-partner-docs
```

`AUDIENCES` in the script is the table: one key per outside reader, which is also the
repo name. The shipped entry is an invented example; replace it.

## Why the deny list derives from the publisher

The same leak happened twice in the spine this came from. The sync discovered a shared
checkout (it carried a generated copy) and wrote the full constitution into it. The fix
was a hand-kept deny list. Four days later a new shared repo was created by a different
workflow, the list did not cover it, and the sync did it again; only the publisher's own
commit lock stopped the push.

Nothing was remembered wrong. The guard was a list a human had to update, and the thing
it guards gets created elsewhere. So `workspace_lib.deny_sync_names()` now unions the
hand-kept `deny_sync` with `published_audience_names()`, which parses the `AUDIENCES`
dict out of the publisher with `ast`. Adding an audience denies the sync automatically.
It is parsed, never imported, because executing the publisher would run its argument
parsing; and because a rename inside the publisher would make the parse return an empty
set, which denies nothing extra and reads as a pass, `scripts/tests-shared-repos-never-sync.py`
asserts the parse still finds the audiences, that every one is denied, that ordinary
repos are still targets, and that the scrub aborts on a planted hit. Check 13 runs it on
every commit.

Two independent guards is why the second event was a near miss rather than a leak. Keep
both.
