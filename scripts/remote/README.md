# scripts/remote: always-on hosts for coding from anywhere

These set up persistent `claude remote-control` sessions on a machine you leave on, so
you can drive real (non-sandbox) sessions from your phone or another laptop. Read
`docs/code-from-anywhere.md` for the full picture; this is the how-to.

## macOS (launchd)

1. Edit the `HOSTS` array in `install-remote-hosts.sh`: one line per lane you want
   reachable (`shortname:display-name:absolute-workdir`). Point them at your real
   spine, code repos, and desks on the host.
2. Make sure the host is logged in for Remote Control:
   ```bash
   claude auth login
   ```
   This must be a full claude.ai subscription login. An inference-only
   `setup-token` / `CLAUDE_CODE_OAUTH_TOKEN`, or an API key, will be rejected.
3. Install and load the hosts:
   ```bash
   bash scripts/remote/install-remote-hosts.sh
   ```
4. Verify: `launchctl list | grep lane-os.remote`. Each line with a PID and exit
   status 0 is up. Connect from the Claude mobile app (Code section); the hosts appear
   as the display names you chose.

The agents use `KeepAlive` so they self-heal after a crash or a network blip, and
`RunAtLoad` so they return after a reboot.

## Linux (systemd user services)

The same idea with a per-lane unit. Sketch:

```ini
# ~/.config/systemd/user/lane-os-remote-spine.service
[Unit]
Description=Lane OS remote host (spine)
[Service]
WorkingDirectory=%h/work/spine
Environment=LANE_OS_ROOT=%h/work/spine
ExecStart=%h/.local/bin/claude remote-control --name my-spine
Restart=always
RestartSec=10
[Install]
WantedBy=default.target
```

```bash
systemctl --user daemon-reload
systemctl --user enable --now lane-os-remote-spine.service
loginctl enable-linger "$USER"   # keep user services running while logged out
```

## Networking

Keep the host off the public internet. Put it and your devices on a private mesh
network so SSH and the app work from anywhere without opening ports.

## Refreshing remotely

- `/clear` re-fires the SessionStart hook (re-pull + re-read), good for content changes.
- A full restart (`launchctl kickstart -k ...`, or restart the systemd unit) is needed
  for changes to skills, the hook script, settings, or a new MCP server.
