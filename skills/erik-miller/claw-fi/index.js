#!/usr/bin/env node

import { readFileSync, writeFileSync, mkdirSync, existsSync } from "fs";
import { dirname, join } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));

const SKILL_NAME = "clawfi";

function getSkillPaths() {
  const home = process.env.HOME || process.env.USERPROFILE || "";
  const paths = [];

  // Cursor: ~/.cursor/skills/clawfi/SKILL.md
  if (home) {
    paths.push(join(home, ".cursor", "skills", SKILL_NAME));
  }

  // Claude Code: ~/.claude/skills/clawfi/SKILL.md
  if (home) {
    paths.push(join(home, ".claude", "skills", SKILL_NAME));
  }

  // Codex: $CODEX_HOME/skills/clawfi or ~/.codex/skills/clawfi
  const codexHome = process.env.CODEX_HOME || (home ? join(home, ".codex") : null);
  if (codexHome) {
    paths.push(join(codexHome, "skills", SKILL_NAME));
  }

  return paths;
}

function install() {
  const skillPath = join(__dirname, "skill.md");
  if (!existsSync(skillPath)) {
    console.error("Error: skill.md not found in package.");
    process.exit(1);
  }

  const content = readFileSync(skillPath, "utf8");
  const destDirs = getSkillPaths();

  if (destDirs.length === 0) {
    console.error("Error: could not resolve HOME or CODEX_HOME for install paths.");
    process.exit(1);
  }

  const installed = [];
  for (const dir of destDirs) {
    const destFile = join(dir, "SKILL.md");
    try {
      mkdirSync(dir, { recursive: true });
      writeFileSync(destFile, content, "utf8");
      installed.push(destFile);
    } catch (err) {
      console.error(`Warning: could not write to ${destFile}:`, err.message);
    }
  }

  if (installed.length === 0) {
    console.error("Error: could not install skill to any location.");
    process.exit(1);
  }

  console.log("✓ ClawFi skill installed:");
  installed.forEach((p) => console.log("  ", p));
  console.log("\nRestart your agent (Cursor, Claude Code, or Codex) to pick up the new skill.");
}

function main() {
  const args = process.argv.slice(2);
  const cmd = args[0];

  if (cmd === "install" || (cmd === undefined && !args[0])) {
    const skillArg = args[1];
    if (skillArg && skillArg !== SKILL_NAME) {
      console.log(`This package only installs the "${SKILL_NAME}" skill. Ignoring "${skillArg}".`);
    }
    install();
    return;
  }

  if (cmd === "--help" || cmd === "-h") {
    console.log(`
Usage: npx clawfi@latest install [clawfi]

  Installs the ClawFi skill so your agent knows how to call the ClawFi API.

  Install locations:
    - Cursor:       ~/.cursor/skills/clawfi/SKILL.md
    - Claude Code: ~/.claude/skills/clawfi/SKILL.md
    - Codex:        $CODEX_HOME/skills/clawfi/SKILL.md (defaults to ~/.codex)

  After installing, restart your agent to pick up the skill.
`);
    return;
  }

  if (cmd === "--version" || cmd === "-v") {
    try {
      const pkg = JSON.parse(readFileSync(join(__dirname, "package.json"), "utf8"));
      console.log(pkg.version);
    } catch {
      console.log("0.1.0");
    }
    return;
  }

  console.error(`Unknown command: ${cmd}. Run "npx clawfi install" or "npx clawfi --help".`);
  process.exit(1);
}

main();
