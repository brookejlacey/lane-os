# Philosophy: one window = one topic

Lane OS comes from a single observation: the bottleneck in agentic coding is not the
model, it is **context and coordination**. A capable agent with the wrong context, or
three capable agents fighting over the same files, produces worse results than one
agent that knows exactly where it is and what it owns.

## Two failure modes Lane OS is built to prevent

**1. The amnesiac session.** You open a new session and the agent knows nothing about
your work, your decisions, your constraints, or the person it is helping. You paste
the same background in again. It still guesses. The fix is a durable, structured
context layer (the spine) that every session reads on boot, plus a memory of facts
that survive across sessions.

**2. The clobbering swarm.** The moment you run more than one session at a time, they
start competing to write the same "current state" files. Two sessions update the same
status file, both commit, one push fails, you rebase, something gets lost. The fix is
to give every session exactly one lane it may write, and forbid the rest.

## Why "one window = one topic"

A session that tries to hold your whole world in context holds none of it well. A
session scoped to one topic boots with exactly the right context, writes to exactly
one place, and never collides with the work happening in another window. You, the
human, become the orchestrator across windows; each window is a specialist.

This is the same instinct as good module boundaries in code: high cohesion inside a
lane, low coupling between lanes, and a single shared spine they all read but only one
kind of session may write.

## The human is the orchestrator

Lane OS does not try to make one agent do everything. It makes each agent do one thing
with full context, and makes it safe to run many of them at once. The leverage is in
the parallelism plus the boundaries, not in any single clever session.
