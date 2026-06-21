# Code from anywhere, without a sandbox

The payoff of Lane OS is not just local. Once your lanes and spine exist, you can
drive **real, full-filesystem coding sessions from your phone or any other computer**,
against your actual repos, with your real secrets and CLIs, by keeping a few always-on
sessions running on one machine you leave on.

## The sandbox is not the goal

Most "AI coding from your phone" setups give you a sandbox: a single cloned repo, no
local secrets, changes land as a pull request, and you cannot cross between repos or
run your real operations. That is fine for a tiny edit and useless for real work.

Lane OS gives you the opposite. The remote session is a **normal session on your own
machine**: every repo is there, your credentials are there, your tools are there, and
it can run anything you could run sitting at the keyboard. The only difference is you
are connected to it from somewhere else.

## The architecture

```
   phone (Claude app)  ─┐
                        ├──>  always-on host  ──>  one remote-control session PER LANE
   laptop / SSH        ─┘     (a machine you             each rooted in its lane dir
                              leave running)              (spine, code lane, or desk)
```

- **One always-on machine.** A home server, a spare laptop, a small desktop. Leave it
  powered on and online.
- **One long-lived session per lane.** The host runs a `claude remote-control` process
  for each lane you want to reach, each with its working directory set to that lane.
  Because every host boots inside its lane, it loads the right context and inherits the
  right write boundary with no extra work: the SessionStart hook and the write-lane
  guard do their normal job. Tapping a lane on your phone drops you straight into a
  correctly-scoped session.
- **Two ways in.** Connect from the Claude mobile app (the hosts show up as named
  targets, one per lane), or SSH into the host over a private network for a real shell
  with full control.

## Why one host per lane (not one big host)

A single remote host rooted at your home directory would boot with no lane, no write
boundary, and no injected context. One host per lane means each target you tap is
already the right kind of session: the spine host is your cross-cutting window, a code
host is scoped to that repo, a desk host is scoped to that topic. The same boundaries
that protect your parallel local sessions protect your remote ones.

## Keep them alive

Run each host under a process supervisor so it self-heals:

- **macOS:** a launchd LaunchAgent per lane with `KeepAlive` (relaunch after a crash or
  a network blip) and `RunAtLoad` (come back after reboot).
- **Linux:** a systemd user service per lane with `Restart=always` and
  `WantedBy=default.target`.

`scripts/remote/install-remote-hosts.sh` writes and loads the macOS LaunchAgents for a
list of lanes you define. See `scripts/remote/README.md`.

## Reach the host over a private network

Do not expose the host to the public internet. Put it and your phone/laptop on a
private mesh network (for example, a WireGuard-based mesh) so SSH and direct access
work from anywhere without opening ports. SSH gives you a real shell with Ctrl-C; the
mobile app gives you the managed session UI. Use whichever fits the moment.

## Refresh a remote session without being at the keyboard

The same lifecycle rules apply, and most can be done from the phone:

- **Content changed** (brain, status, code): send `/clear`, which re-fires the
  SessionStart hook (re-pull + re-read), or run a `/catchup` skill.
- **Instructions changed** (constitution, a skill, the hook script, settings): a full
  restart is the only guarantee, because those bind at process start. Restarting a host
  is just kicking its supervised process; the new session reappears as the same target.

Mnemonic, unchanged: instructions changed = restart, content changed = refresh.

## The auth gotcha (read this before you debug for an hour)

Remote Control requires a **full-scope claude.ai subscription login** on the host. Run
the interactive login once on the host:

```bash
claude auth login
```

Two things that look like they should work but do not:

- **`claude setup-token` / `CLAUDE_CODE_OAUTH_TOKEN`** produces an inference-only token.
  Remote Control rejects it with a message telling you to run a full login.
- **An API key** is not a subscription login. Remote Control needs the claude.ai
  subscription auth, not an API key.

If your hosts crash-loop and the logs show `401 ... Remote Control is only available
with claude.ai subscriptions`, the fix is `claude auth login` on the host. The same
applies if you ever shared one login across machines and token rotation invalidated
one of them: give the host its own login rather than copying credentials around.
