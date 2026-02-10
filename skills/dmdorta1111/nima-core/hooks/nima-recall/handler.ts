/**
 * NIMA Auto-Recall Hook
 * 
 * Queries NIMA vector store on session bootstrap and injects relevant
 * memories into the agent's context. Works with any bot running nima-core.
 */

import { execFileSync } from "child_process";
import { existsSync, readFileSync } from "fs";
import { join } from "path";

interface HookEvent {
  type: string;
  action: string;
  sessionKey: string;
  timestamp: Date;
  messages: string[];
  context: {
    workspaceDir?: string;
    sessionFile?: string;
    bootstrapFiles?: Array<{ path: string; content: string; source: string }>;
    cfg?: Record<string, unknown>;
  };
}

type HookHandler = (event: HookEvent) => Promise<void> | void;

/**
 * Extract recent conversation text from session transcript
 */
function extractRecentContext(sessionFile: string, maxLines: number = 200): string {
  try {
    const content = readFileSync(sessionFile, "utf-8");
    const lines = content.split("\n").slice(-maxLines);
    
    const messages: string[] = [];
    let currentRole = "";
    let currentText = "";

    for (const line of lines) {
      if (line.startsWith("## User") || line.startsWith("## Assistant")) {
        if (currentText && currentRole) {
          messages.push(`${currentRole}: ${currentText.trim()}`);
        }
        currentRole = line.startsWith("## User") ? "User" : "Assistant";
        currentText = "";
      } else if (currentRole && line.trim()) {
        currentText += line + " ";
      }
    }

    if (currentText && currentRole) {
      messages.push(`${currentRole}: ${currentText.trim()}`);
    }

    return messages.slice(-10).join("\n\n") || "";
  } catch (err) {
    console.debug("[nima-recall] Failed to extract context:", err instanceof Error ? err.message : String(err));
    return "";
  }
}

/**
 * Query NIMA via Python CLI
 */
function queryNIMA(workspaceDir: string, query: string, limit: number, timeout: number): string | null {
  try {
    // Try workspace-local nima_core first, then pip-installed
    const localPath = join(workspaceDir, "nima-core", "nima_core");
    const localExists = existsSync(localPath);

    // Python script reads query/limit from stdin JSON — no shell interpolation
    const pythonScript = [
      "import sys, json",
      localExists ? "sys.path.insert(0, sys.argv[1])" : "",
      "data = json.loads(sys.stdin.read())",
      "from nima_core import NimaCore",
      "n = NimaCore()",
      "results = n.recall(data['query'], top_k=data['limit'])",
      "[print(f'{r.get(\"who\",\"?\")}|{r.get(\"what\",\"\")}') for r in results]",
    ].filter(Boolean).join("; ");

    const args = ["-c", pythonScript];
    if (localExists) args.push(join(workspaceDir, "nima-core"));

    const stdinData = JSON.stringify({ query: query.substring(0, 500), limit });

    const result = execFileSync("python3", args, {
      cwd: workspaceDir,
      timeout,
      encoding: "utf-8",
      input: stdinData,
      stdio: ["pipe", "pipe", "pipe"],
    }).trim();

    return result || null;
  } catch (err) {
    const isTimeout =
      (err as NodeJS.ErrnoException)?.code === "ETIMEDOUT" ||
      (err as NodeJS.ErrnoException)?.signal === "SIGTERM";
    if (isTimeout) {
      console.log("[nima-recall] Timeout — embeddings may be loading");
    } else {
      const msg = err instanceof Error ? err.message : String(err);
      console.error("[nima-recall] Query error:", msg.substring(0, 200));
    }
    return null;
  }
}

/**
 * Format results as markdown
 */
function formatResults(raw: string, querySnippet: string): string {
  const lines = raw.split("\n").filter((l) => l.trim());
  if (lines.length === 0) return "";

  let md = `# 🔮 NIMA Recall\n\n`;
  md += `**Context:** ${querySnippet.substring(0, 150)}${querySnippet.length > 150 ? "..." : ""}\n\n`;

  for (let i = 0; i < lines.length; i++) {
    const parts = lines[i].split("|");
    const who = parts[0]?.trim() || "?";
    const what = parts.slice(1).join("|").trim() || lines[i];
    const truncated = what.length > 200 ? what.substring(0, 200) + "..." : what;
    md += `**[${i + 1}]** ${who}: ${truncated}\n\n`;
  }

  md += `---\n*${lines.length} memories retrieved by nima-recall*\n`;
  return md;
}

const handler: HookHandler = async (event) => {
  // Only handle bootstrap
  if (event.type !== "agent" || event.action !== "bootstrap") return;

  // Skip non-conversational sessions
  if (event.sessionKey?.includes(":subagent:")) return;
  if (event.sessionKey?.includes("heartbeat")) return;

  const workspaceDir = event.context.workspaceDir;
  if (!workspaceDir) return;

  // Config
  const hookConfig = (event.context.cfg as any)?.hooks?.internal?.entries?.["nima-recall"] || {};
  if (hookConfig.enabled === false) return;
  const limit = hookConfig.limit ?? 3;
  const timeout = hookConfig.timeout ?? 15000;

  try {
    // Extract conversation context
    let queryContext = "";
    if (event.context.sessionFile && existsSync(event.context.sessionFile)) {
      queryContext = extractRecentContext(event.context.sessionFile);
    }

    // Need meaningful context to query
    if (queryContext.length < 20) {
      console.log("[nima-recall] Insufficient context, skipping");
      return;
    }

    // Query NIMA
    const results = queryNIMA(workspaceDir, queryContext, limit, timeout);
    if (!results) return;

    // Format and inject
    const md = formatResults(results, queryContext);
    if (!md) return;

    if (!event.context.bootstrapFiles) event.context.bootstrapFiles = [];
    event.context.bootstrapFiles.push({
      path: "NIMA_RECALL.md",
      content: md,
      source: "nima-recall",
    });

    console.log(`[nima-recall] ✓ Injected memories into context`);
  } catch (err) {
    console.error("[nima-recall]", err instanceof Error ? err.message : String(err));
  }
};

export default handler;
