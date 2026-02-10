/**
 * NIMA Bootstrap Hook
 * 
 * Injects NIMA cognitive memory status into session context on bootstrap.
 * Works with any bot that has nima-core installed.
 */

import { execFileSync } from "child_process";
import { existsSync } from "fs";
import { join } from "path";

interface HookEvent {
  type: string;
  action: string;
  sessionKey: string;
  timestamp: Date;
  messages: string[];
  context: {
    workspaceDir?: string;
    bootstrapFiles?: Array<{ path: string; content: string; source: string }>;
    cfg?: Record<string, unknown>;
  };
}

type HookHandler = (event: HookEvent) => Promise<void> | void;

const handler: HookHandler = (event: HookEvent) => {
  const { sessionKey, context } = event;
  const workspaceDir = context.workspaceDir;

  // Skip non-conversational sessions
  if (sessionKey?.includes(":subagent:")) return;
  if (sessionKey?.includes("heartbeat")) return;
  if (!workspaceDir) return;

  // Get timeout from config
  const hookConfig = (context.cfg as any)?.hooks?.internal?.entries?.["nima-bootstrap"] || {};
  const timeout = hookConfig.timeout || 15000;

  try {
    // First check if nima_core is importable at all
    const checkScript = `try:\n    from nima_core import NimaCore\n    print('OK')\nexcept Exception as e:\n    print(f'NOT_FOUND: {e}')`;
    
    let checkResult: string;
    try {
      checkResult = execFileSync("python3", ["-c", checkScript], {
        cwd: workspaceDir,
        timeout: 5000,
        encoding: "utf-8",
        stdio: ["pipe", "pipe", "pipe"],
      }).trim();
    } catch (e) {
      // Python or nima_core not available - silently skip
      console.log("[nima-bootstrap] NIMA not installed, skipping");
      return;
    }

    if (checkResult.includes("NOT_FOUND")) {
      // nima_core not available - silently skip
      console.log("[nima-bootstrap] NIMA not installed, skipping");
      return;
    }

    // Find nima_core — check workspace first, then pip
    const localPath = join(workspaceDir, "nima-core", "nima_core");
    const localExists = existsSync(localPath);

    // Build Python script as argument (no shell interpolation of paths)
    const pythonScript = [
      localExists ? `import sys; sys.path.insert(0, sys.argv[1])` : "",
      `from nima_core import NimaCore`,
      `n = NimaCore()`,
      `s = n.status()`,
      `print(f'memories={s.get("memory_count", 0)}')`,
      `config = s.get("config", {})`,
      `v2 = config.get("v2_enabled", False) if isinstance(config, dict) else False`,
      `print(f'v2={v2}')`,
    ].filter(Boolean).join("; ");

    // Use execFileSync to avoid shell — pass workspace path as argv[1]
    const args = ["-c", pythonScript];
    if (localExists) args.push(join(workspaceDir, "nima-core"));

    const result = execFileSync("python3", args, {
      cwd: workspaceDir,
      timeout,
      encoding: "utf-8",
      stdio: ["pipe", "pipe", "pipe"],
    }).trim();

    // Parse output
    const memoryMatch = result.match(/memories=(\d+)/);
    const v2Match = result.match(/v2=(\w+)/);
    const memoryCount = memoryMatch ? memoryMatch[1] : "unknown";
    const v2Enabled = v2Match ? v2Match[1] : "unknown";

    const statusContent = `# NIMA Status

**Generated:** ${new Date().toISOString()}

## System
- **Memory Count:** ${memoryCount}
- **V2 Cognitive Stack:** ${v2Enabled}
- **Installation:** ${localExists ? "Local (workspace)" : "pip package"}

## Capabilities
NIMA provides persistent cognitive memory across sessions. Use \`nima.recall(query)\` to search memories and \`nima.capture(who, what)\` to store important moments.

---
*NIMA (Noosphere Integrated Memory Architecture) — emotion-aware memory with principled consolidation.*
`;

    // Inject
    if (!context.bootstrapFiles) context.bootstrapFiles = [];
    context.bootstrapFiles.push({
      path: "NIMA_STATUS.md",
      content: statusContent,
      source: "nima-bootstrap",
    });

    console.log(`[nima-bootstrap] ✓ ${memoryCount} memories, v2=${v2Enabled}`);
  } catch (error) {
    // Silently skip on any error - don't spam logs
    console.log("[nima-bootstrap] NIMA not available, skipping");
  }
};

export default handler;
