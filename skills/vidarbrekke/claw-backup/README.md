# ClawBackup

Backs up your OpenClaw customizations (memory, config, skills, workspace) to Google Drive on a schedule. Works on macOS, Linux, and Windows (via Git Bash or WSL).

## What gets backed up

- **Clawd memory** — your project memory folder
- **OpenClaw config** — `openclaw.json`, skills, modules, workspace, cron jobs
- **Clawd scripts** — backup script, LaunchAgent plist (macOS)
- **CursorApps/clawd** — skills source, session proxy, docs (excluding `node_modules`)

## Prerequisites

- **Node.js** — [Download](https://nodejs.org/) (for running setup)
- **rclone** — [Download](https://rclone.org/install/) and configured for Google Drive
- **Bash** — included on macOS/Linux; use Git Bash on Windows. **If you use WSL**, run setup inside your WSL terminal (e.g. `node setup.js` from WSL), not from Windows PowerShell, so paths are generated for Linux.

## Install (choose one)

### Option A: One command (no git required)

Run this in your terminal. It downloads and runs the setup interactively:

```bash
curl -fsSL https://raw.githubusercontent.com/vidarbrekke/ClawBackup/main/setup.js | node
```

### Option B: Clone the repo

```bash
git clone https://github.com/vidarbrekke/ClawBackup.git
cd ClawBackup
node setup.js
```

## Run setup

1. Run the setup (using Option A or B above).
2. Answer the prompts. Press Enter to accept the default in brackets. All paths use your system’s home directory and what you type — nothing is hardcoded to a specific username.
3. The setup writes a customized `backup_enhanced.sh` into your project’s `scripts/` folder (paths are resolved to absolute so cron/launchd work from any working directory).
4. If you chose `launchd` (macOS) or `cron` (Linux), follow the printed commands to enable scheduled backups.

To regenerate the backup script and plist with default paths only (no prompts), run `node setup.js --defaults`.

## Before first backup

1. **Configure rclone for Google Drive:**
   ```bash
   rclone config
   ```
   Create a remote (e.g. `googleDrive`) and complete the OAuth flow.

2. **Test a backup:**
   ```bash
   ~/clawd/scripts/backup_enhanced.sh
   ```
   (Use the path the setup printed for your system.)

## Schedule (optional)

- **macOS:** The setup generates a LaunchAgent plist. Install with the printed commands (copy to `~/Library/LaunchAgents/` and `launchctl load` — no sudo for the agent). Or run the universal installer: `./install-launchagent.sh` (it searches common locations; if your project is elsewhere, pass the plist path: `./install-launchagent.sh /path/to/com.openclaw.backup.plist`). If you had an old system-wide daemon, the installer may ask for your password once to remove it. Backups run daily at 11:00 under your user so rclone uses your config.
- **Linux:** Add the printed cron line to `crontab -e`.
- **Windows:** Use Task Scheduler to run the backup script daily via Git Bash or WSL.

## Troubleshooting

- **Backup fails or rclone “remote not found”:** Run `rclone config` and ensure the remote name matches what you entered at setup (e.g. `googleDrive`). On macOS, use the LaunchAgent (not LaunchDaemon) so the job runs as your user and sees `~/.config/rclone`.
- **Paths wrong after moving home/project:** Run `node setup.js` again with the new paths, then reinstall the scheduler (e.g. `./install-launchagent.sh` on macOS).
- **Check logs:** Local backup log: `$LOCAL_BACKUP_DIR/backup.log`; launchd stdout/stderr: `$LOCAL_BACKUP_DIR/launchd.log` and `launchd.err` (paths from your setup).

## For maintainers / AI-assisted edits

To reduce oversights when editing this repo (e.g. destructive ops, path edge cases), this repo includes a Cursor rule: [.cursor/rules/safety-destructive-ops.mdc](.cursor/rules/safety-destructive-ops.mdc). You can copy that file into your OpenClaw or clawd project’s `.cursor/rules/` so the same checks apply there.

## License

MIT
