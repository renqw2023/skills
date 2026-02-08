#!/usr/bin/env node
"use strict";

const fs = require("fs");
const os = require("os");
const path = require("path");
const readline = require("readline");

const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
const ask = (q) => new Promise((resolve) => rl.question(q, resolve));

const home = os.homedir();
const defaults = {
  projectDir: path.join(home, "clawd"),
  openclawDir: path.join(home, ".openclaw"),
  cursorappsClawd: path.join(home, "Dev", "CursorApps", "clawd"),
  localBackupDir: path.join(home, "clawd", "MoltBackups", "Memory"),
  gdriveRemote: "googleDrive:",
  gdriveDest: "MoltBackups/Memory/",
  retentionDays: "7",
  schedule: os.platform() === "darwin" ? "launchd" : "cron"
};

/** Resolve to absolute path; expand leading ~ to homedir so cron/launchd work from any CWD. */
function resolveDir(p) {
  if (typeof p !== "string" || !p.trim()) return p;
  const expanded = p.trim().replace(/^~(?=\/|$)/, home);
  return path.resolve(expanded);
}

/** Paths in generated Bash script must use forward slashes (Windows compatibility). */
const toPosix = (p) => (typeof p === "string" ? p.split(path.sep).join(path.posix.sep) : p);

/** Escape double quotes so injected values don't break Bash variable syntax. */
const escapeBash = (s) => (typeof s === "string" ? s.replace(/\\/g, "\\\\").replace(/"/g, '\\"') : String(s ?? ""));

/** Escape for XML plist string content. */
const escapePlist = (s) =>
  String(s ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&apos;");

/** Warn if path does not exist; return path unchanged. */
function validatePath(label, p) {
  if (p && !fs.existsSync(p)) {
    console.warn(`Warning: "${label}" does not exist: ${p}`);
  }
  return p;
}

function safeWrite(filePath, content) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  fs.writeFileSync(filePath, content, "utf8");
}

function writeScriptWithBackup(scriptPath, content) {
  if (fs.existsSync(scriptPath)) {
    const bak = scriptPath + ".bak";
    fs.renameSync(scriptPath, bak);
    console.warn(`Existing script backed up to: ${bak}`);
  }
  safeWrite(scriptPath, content);
}

function buildBackupScript(cfg) {
  const raw = (key, fallback) => (cfg[key] != null && String(cfg[key]).trim() !== "" ? cfg[key] : fallback);
  const p = (key, fallback) => escapeBash(toPosix(raw(key, fallback) ?? ""));
  const s = (key, fallback) => escapeBash(raw(key, fallback) ?? "");
  const retention = String(raw("retentionDays", "7")).replace(/[^0-9]/g, "") || "7";
  return `#!/bin/bash
set -e

PROJECT_DIR="${p("projectDir", defaults.projectDir)}"
SOURCE_DIR="$PROJECT_DIR/memory"
OPENCLAW_DIR="${p("openclawDir", defaults.openclawDir)}"
CURSORAPPS_CLAWD="${p("cursorappsClawd", defaults.cursorappsClawd)}"
LOCAL_BACKUP_DIR="${p("localBackupDir", defaults.localBackupDir)}"
LOG_FILE="$LOCAL_BACKUP_DIR/backup.log"
RETENTION_DAYS=${retention}
RCLONE_REMOTE="${s("gdriveRemote", defaults.gdriveRemote)}"
GDRIVE_DEST_DIR="${s("gdriveDest", defaults.gdriveDest)}"

log_message() {
  local message="$1"
  echo "$(date +"%Y-%m-%d %H:%M:%S") - $message" | tee -a "$LOG_FILE"
}

if [ ! -d "$LOCAL_BACKUP_DIR" ]; then
  mkdir -p "$LOCAL_BACKUP_DIR"
  log_message "Created local backup directory '$LOCAL_BACKUP_DIR'."
fi

BACKUP_DATE=$(date +"%Y-%m-%d_%H-%M-%S")
ARCHIVE_NAME="clawd_memory_backup_\${BACKUP_DATE}.tar.gz"
FULL_ARCHIVE_PATH="$LOCAL_BACKUP_DIR/$ARCHIVE_NAME"
TEMP_DIR=$(mktemp -d)
trap 'rm -rf "$TEMP_DIR"' EXIT
STAGING_DIR="$TEMP_DIR/clawd_backup_$BACKUP_DATE"

log_message "Preparing backup staging area..."
mkdir -p "$STAGING_DIR"

if [ -d "$SOURCE_DIR" ]; then
  cp -R "$SOURCE_DIR" "$STAGING_DIR/"
  log_message "Staged memory directory."
fi

MD_COUNT=$(find "$PROJECT_DIR" -maxdepth 1 -type f -name "*.md" 2>/dev/null | wc -l)
if [ "$MD_COUNT" -gt 0 ]; then
  mkdir -p "$STAGING_DIR/root_md_files"
  find "$PROJECT_DIR" -maxdepth 1 -type f -name "*.md" -exec cp {} "$STAGING_DIR/root_md_files/" \\; 2>/dev/null
  log_message "Staged $MD_COUNT .md files from project root."
fi

if [ -d "$PROJECT_DIR/scripts" ]; then
  mkdir -p "$STAGING_DIR/clawd_scripts"
  cp -R "$PROJECT_DIR/scripts"/* "$STAGING_DIR/clawd_scripts/" 2>/dev/null || true
  log_message "Staged clawd/scripts."
fi

OPENCLAW_STAGE="$STAGING_DIR/openclaw_config"
mkdir -p "$OPENCLAW_STAGE"
if [ -d "$OPENCLAW_DIR" ]; then
  [ -f "$OPENCLAW_DIR/openclaw.json" ] && cp "$OPENCLAW_DIR/openclaw.json" "$OPENCLAW_STAGE/"
  [ -d "$OPENCLAW_DIR/skills" ] && cp -R "$OPENCLAW_DIR/skills" "$OPENCLAW_STAGE/"
  [ -d "$OPENCLAW_DIR/modules" ] && cp -R "$OPENCLAW_DIR/modules" "$OPENCLAW_STAGE/"
  [ -f "$OPENCLAW_DIR/round-robin-models.json" ] && cp "$OPENCLAW_DIR/round-robin-models.json" "$OPENCLAW_STAGE/"
  [ -d "$OPENCLAW_DIR/workspace" ] && cp -R "$OPENCLAW_DIR/workspace" "$OPENCLAW_STAGE/"
  [ -d "$OPENCLAW_DIR/workspace-local-ops" ] && cp -R "$OPENCLAW_DIR/workspace-local-ops" "$OPENCLAW_STAGE/"
  [ -f "$OPENCLAW_DIR/cron/jobs.json" ] && mkdir -p "$OPENCLAW_STAGE/cron" && cp "$OPENCLAW_DIR/cron/jobs.json" "$OPENCLAW_STAGE/cron/"
  log_message "Staged ~/.openclaw custom config."
fi

if [ -d "$CURSORAPPS_CLAWD" ]; then
  CLAWD_STAGE="$STAGING_DIR/cursorapps_clawd"
  mkdir -p "$CLAWD_STAGE"
  if command -v rsync >/dev/null 2>&1; then
    rsync -a --exclude='node_modules' --exclude='test-results' --exclude='.last-run.json' "$CURSORAPPS_CLAWD/" "$CLAWD_STAGE/"
  else
    cp -R "$CURSORAPPS_CLAWD"/* "$CLAWD_STAGE/" 2>/dev/null || true
    rm -rf "$CLAWD_STAGE/node_modules" "$CLAWD_STAGE/test-results" 2>/dev/null
  fi
  log_message "Staged Dev/CursorApps/clawd."
fi

log_message "Creating backup archive '$FULL_ARCHIVE_PATH'..."
tar -czf "$FULL_ARCHIVE_PATH" -C "$TEMP_DIR" "clawd_backup_$BACKUP_DATE"
log_message "Backup archive created successfully."

log_message "Starting rclone transfer to Google Drive..."
if [ -t 1 ]; then
  rclone copy "$FULL_ARCHIVE_PATH" "$RCLONE_REMOTE$GDRIVE_DEST_DIR" --progress
else
  rclone copy "$FULL_ARCHIVE_PATH" "$RCLONE_REMOTE$GDRIVE_DEST_DIR" --stats-one-line --stats 10s
fi
log_message "Backup successfully transferred to Google Drive."

log_message "Applying retention policy ($RETENTION_DAYS days)..."
find "$LOCAL_BACKUP_DIR" -maxdepth 1 -type f -name 'clawd_memory_backup_*.tar.gz' -mtime +"$RETENTION_DAYS" -print -delete | while read -r old_backup; do
  log_message "Deleted old local backup: '$old_backup'."
done
log_message "Cleaning up remote backups older than $RETENTION_DAYS days..."
if [ -n "$RCLONE_REMOTE" ] && [ -n "$GDRIVE_DEST_DIR" ] && [ "$GDRIVE_DEST_DIR" != "/" ]; then
  rclone delete --min-age \${RETENTION_DAYS}d "$RCLONE_REMOTE$GDRIVE_DEST_DIR" 2>/dev/null || true
else
  log_message "Skipping remote cleanup: remote or dest not set or dest is root."
fi

log_message "Backup process completed successfully."
exit 0
`;
}

function buildLaunchdPlist(scriptPath, localBackupDir) {
  const logPath = escapePlist(toPosix(path.join(localBackupDir, "launchd.log")));
  const errPath = escapePlist(toPosix(path.join(localBackupDir, "launchd.err")));
  const scriptPathPosix = escapePlist(toPosix(scriptPath));
  return `<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
  <dict>
    <key>Label</key>
    <string>com.openclaw.backup</string>
    <key>ProgramArguments</key>
    <array>
      <string>${scriptPathPosix}</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
      <key>Hour</key>
      <integer>11</integer>
      <key>Minute</key>
      <integer>0</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>${logPath}</string>
    <key>StandardErrorPath</key>
    <string>${errPath}</string>
  </dict>
</plist>
`;
}

function normalizeSchedule(input) {
  const v = (input || "").trim().toLowerCase();
  if (v === "launchd" || v === "cron" || v === "none") return v;
  if ((input || "").trim() !== "") console.warn(`Unknown schedule "${input}"; using "${defaults.schedule}".`);
  return defaults.schedule;
}

async function main() {
  const useDefaults = process.argv.includes("--defaults");
  if (useDefaults) {
    const cfg = {
      projectDir: resolveDir(defaults.projectDir),
      openclawDir: resolveDir(defaults.openclawDir),
      cursorappsClawd: resolveDir(defaults.cursorappsClawd),
      localBackupDir: resolveDir(defaults.localBackupDir),
      gdriveRemote: defaults.gdriveRemote,
      gdriveDest: defaults.gdriveDest,
      retentionDays: defaults.retentionDays
    };
    const scriptsDir = path.join(cfg.projectDir, "scripts");
    const scriptPath = path.join(scriptsDir, "backup_enhanced.sh");
    writeScriptWithBackup(scriptPath, buildBackupScript(cfg));
    fs.chmodSync(scriptPath, 0o755);
    console.log(`Backup script written to: ${scriptPath}`);
    if (os.platform() === "darwin") {
      const plistPath = path.join(scriptsDir, "com.openclaw.backup.plist");
      safeWrite(plistPath, buildLaunchdPlist(scriptPath, cfg.localBackupDir));
      console.log(`Plist written to: ${plistPath}`);
    }
    return;
  }
  console.log("ClawBackup Setup (interactive)\n");
  const projectDir = resolveDir((await ask(`Project dir [${defaults.projectDir}]: `)).trim() || defaults.projectDir);
  const openclawDir = resolveDir((await ask(`~/.openclaw dir [${defaults.openclawDir}]: `)).trim() || defaults.openclawDir);
  const cursorappsClawd = resolveDir((await ask(`Dev/CursorApps/clawd dir [${defaults.cursorappsClawd}]: `)).trim() || defaults.cursorappsClawd);
  const localBackupDir = resolveDir((await ask(`Local backup dir [${defaults.localBackupDir}]: `)).trim() || defaults.localBackupDir);
  validatePath("Project dir", projectDir);
  validatePath("~/.openclaw dir", openclawDir);
  validatePath("Dev/CursorApps/clawd dir", cursorappsClawd);
  validatePath("Local backup dir", localBackupDir);
  const gdriveRemote = (await ask(`rclone remote [${defaults.gdriveRemote}]: `)).trim() || defaults.gdriveRemote;
  const gdriveDest = (await ask(`GDrive dest path [${defaults.gdriveDest}]: `)).trim() || defaults.gdriveDest;
  const retentionDays = (await ask(`Retention days [${defaults.retentionDays}]: `)).trim() || defaults.retentionDays;
  const scheduleInput = (await ask(`Schedule (launchd|cron|none) [${defaults.schedule}]: `)).trim() || defaults.schedule;
  const schedule = normalizeSchedule(scheduleInput);

  const cfg = { projectDir, openclawDir, cursorappsClawd, localBackupDir, gdriveRemote, gdriveDest, retentionDays };
  const scriptsDir = path.join(projectDir, "scripts");
  const scriptPath = path.join(scriptsDir, "backup_enhanced.sh");
  writeScriptWithBackup(scriptPath, buildBackupScript(cfg));
  fs.chmodSync(scriptPath, 0o755);
  console.log(`\nBackup script written to: ${scriptPath}`);

  if (schedule === "launchd" && os.platform() === "darwin") {
    const plistPath = path.join(scriptsDir, "com.openclaw.backup.plist");
    const launchAgentsDir = path.join(home, "Library", "LaunchAgents");
    safeWrite(plistPath, buildLaunchdPlist(scriptPath, localBackupDir));
    console.log(`Launchd plist written to: ${plistPath}`);
    console.log(`\nInstall the scheduler (run as your user, do not use sudo):`);
    console.log(`  mkdir -p "${launchAgentsDir}"`);
    console.log(`  cp "${plistPath}" "${path.join(launchAgentsDir, "com.openclaw.backup.plist")}"`);
    console.log(`  launchctl load "${path.join(launchAgentsDir, "com.openclaw.backup.plist")}"`);
  } else if (schedule === "cron") {
    console.log(`\nAdd this line to crontab (crontab -e):`);
    console.log(`  0 11 * * * ${scriptPath}`);
  } else {
    console.log("\nScheduler not configured. Run the backup script manually or set up cron/launchd.");
  }

  console.log("\nNext steps:");
  console.log("  1. Ensure rclone is configured: rclone config");
  console.log(`  2. Test run: ${scriptPath}`);
}

main().catch((err) => { console.error(err); process.exit(1); }).finally(() => rl.close());
