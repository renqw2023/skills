# Claw Backup

Back up your OpenClaw customizations (memory, config, skills, workspace) to Google Drive on a schedule. Works on macOS, Linux, and Windows (via Git Bash or WSL).

## What it does

- Backs up **clawd memory**, **~/.openclaw** (config, skills, modules, workspace, cron), **clawd/scripts**, and **Dev/CursorApps/clawd** (excluding `node_modules`)
- Runs on a schedule (macOS LaunchAgent, Linux cron, or Windows Task Scheduler)
- Applies local and remote retention so old backups are pruned

## Quick start

1. **Prerequisites:** Node.js, [rclone](https://rclone.org/install/) configured for Google Drive, and Bash (or Git Bash on Windows).

2. **One-command setup (no git required):**
   ```bash
   curl -fsSL https://raw.githubusercontent.com/vidarbrekke/ClawBackup/main/setup.js | node
   ```
   Or clone and run setup:
   ```bash
   git clone https://github.com/vidarbrekke/ClawBackup.git
   cd ClawBackup
   node setup.js
   ```

3. Follow the prompts (or use `node setup.js --defaults` for default paths). Then run the printed test command and install the scheduler as shown.

## Repo and contributions

- **Code and full docs:** [github.com/vidarbrekke/ClawBackup](https://github.com/vidarbrekke/ClawBackup)
- **Improvements welcome:** Open issues or pull requests on the GitHub repo. The project is open for refinements, fixes, and features from any OpenClaw user.

## License

MIT
