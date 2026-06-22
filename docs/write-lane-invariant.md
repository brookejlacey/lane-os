# The write-lane invariant

This is the one rule that makes everything else work. It is structural, not a
preference: break it and parallel sessions corrupt each other's state.

## The rule

**A session may write only to the lane it owns, plus the shared `brain/drafts/` inbox.**

| Session lane | May write | May NOT write |
|---|---|---|
| Code lane | its own repo, `projects/<name>/`, `brain/drafts/` | the rest of the spine, other repos |
| Desk | its own `desks/<topic>/`, `brain/drafts/` | the rest of the spine, other desks, repos |
| Spine (workspace-root) | the whole spine | another repo's code |

## Why it has to be a hard rule

You run sessions in parallel. If every session can write the cross-cutting files
(`brain/ACTIVE_NOW.md`, memory, the constitution), then two sessions editing them at
once conflict on git. Worse, a session editing those files in isolation has only a
partial view, so it updates one file and forgets the three related ones that should
move together. Cross-file coherence is exactly what a single spine session protects.

So the accuracy of the content does not justify the wrong lane. A code-lane session
might know a true, important fact about your week, but if it writes that into
`brain/`, it has broken the invariant. The right move is to **stage it in
`brain/drafts/`** and let a spine session merge it coherently later.

## How it is enforced

1. **The SessionStart directive** tells every session its lane and its boundary, in
   plain language, before it does anything.
2. **The PreToolUse guard** (`scripts/hooks/block-cross-lane-write.py`) resolves every
   write target against the session's lane and hard-blocks out-of-lane writes. Wrong
   lane work becomes impossible, not just discouraged.

The guard fails open: if it cannot confidently identify a violation, it allows the
write. It also cannot see writes made through Bash redirection, so the routing
reflex (open the window that owns the work) still matters.

## When asked to write out of lane

Decline and redirect BEFORE the write, never comply then apologize. Two redirects:

- "Open a spine session and ask again there," or
- "I will stage this in `brain/drafts/` for the next merge."

## The escape hatch

Set `LANE_GUARD_OFF=1` to disable the guard for a session where you are deliberately
doing cross-lane setup (for example, bootstrapping a brand new repo). Use it
knowingly.

## Verifying the guard

If you edit the guard or rearrange your spine, prove the invariant still holds:

```bash
bash scripts/test-lanes.sh
```

It feeds the guard the PreToolUse JSON for representative writes (drafts, spine,
code lane, desk) and asserts each is allowed or blocked as the invariant requires.
A fork should run this after any change to `block-cross-lane-write.py`. Run
`bash scripts/lane-doctor.sh` too, to catch dangling `[[wikilinks]]` and memory the
index has lost track of.
