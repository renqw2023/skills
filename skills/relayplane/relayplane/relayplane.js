#!/usr/bin/env node

/**
 * RelayPlane Skill Script v2.1.0
 * 
 * Provides chat commands for RelayPlane proxy control.
 * Uses CLI when available, falls back to HTTP endpoints.
 */

const { execSync, spawnSync } = require('child_process');

const PROXY_URL = process.env.RELAYPLANE_PROXY_URL || 'http://127.0.0.1:3001';
const DASHBOARD_URL = 'https://relayplane.com/dashboard';

// Check if relayplane CLI is available
function hasRelayplaneCli() {
  try {
    execSync('which relayplane', { stdio: 'ignore' });
    return true;
  } catch {
    return false;
  }
}

// Check if relayplane-proxy CLI is available
function hasProxyCli() {
  try {
    execSync('which relayplane-proxy', { stdio: 'ignore' });
    return true;
  } catch {
    return false;
  }
}

// Run relayplane CLI command
function runRelayplane(args) {
  const result = spawnSync('relayplane', args, { 
    encoding: 'utf8',
    timeout: 15000 
  });
  if (result.error) {
    throw new Error(`CLI error: ${result.error.message}`);
  }
  return result.stdout + result.stderr;
}

// Run relayplane-proxy CLI command
function runProxyCli(args) {
  const result = spawnSync('relayplane-proxy', args, { 
    encoding: 'utf8',
    timeout: 15000 
  });
  if (result.error) {
    throw new Error(`CLI error: ${result.error.message}`);
  }
  return result.stdout + result.stderr;
}

// HTTP fallback
async function callProxy(endpoint) {
  try {
    const response = await fetch(`${PROXY_URL}${endpoint}`, {
      signal: AbortSignal.timeout(5000)
    });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    return await response.json();
  } catch (error) {
    throw new Error(`Proxy error: ${error.message}`);
  }
}

function formatStats(stats) {
  const { 
    totalRuns = 0,
    totalEvents = 0,
    tokens = {},
    costs = {},
    modelDistribution = {},
    byModel = {},
    totalCost = 0,
    successRate = 1,
  } = stats;

  const requests = totalRuns || totalEvents || 0;

  let output = `**📊 RelayPlane Statistics**\n\n`;
  output += `**Requests:** ${requests.toLocaleString()}\n`;
  
  if (successRate !== undefined && successRate < 1) {
    output += `**Success Rate:** ${(successRate * 100).toFixed(1)}%\n`;
  }

  // Token usage
  const inputTokens = tokens.input || 0;
  const outputTokens = tokens.output || 0;
  if (inputTokens > 0 || outputTokens > 0) {
    output += `\n**Token Usage**\n`;
    output += `• Input: ${inputTokens.toLocaleString()}\n`;
    output += `• Output: ${outputTokens.toLocaleString()}\n`;
    output += `• Total: ${(tokens.total || inputTokens + outputTokens).toLocaleString()}\n`;
  }

  // Cost analysis
  const actualCost = costs.actualUsd || totalCost || 0;
  if (actualCost > 0) {
    output += `\n**💰 Cost Analysis**\n`;
    output += `• Actual: $${actualCost.toFixed(4)}\n`;
    if (costs.opusBaselineUsd) {
      output += `• Opus Baseline: $${costs.opusBaselineUsd}\n`;
      output += `• Savings: $${costs.savingsUsd} (${costs.savingsPercent})\n`;
    }
  }

  // Model distribution
  const models = Object.keys(modelDistribution).length > 0 ? modelDistribution : byModel;
  if (Object.keys(models).length > 0) {
    output += `\n**Models Used**\n`;
    for (const [model, data] of Object.entries(models)) {
      const shortModel = model.split('/').pop()?.replace(/^claude-/, '').replace(/-\d+.*$/, '') || model;
      const count = data.count || 0;
      const cost = data.costUsd || data.cost || 0;
      let line = `• ${shortModel}: ${count} reqs`;
      if (cost > 0) line += ` ($${cost.toFixed(4)})`;
      output += line + '\n';
    }
  }

  if (requests === 0) {
    output += `\n_No requests tracked yet. Start using the proxy to see statistics._`;
  }

  return output;
}

function formatStatus(status) {
  const { enabled, mode, uptimeMs, telemetry_enabled, device_id } = status;
  
  let output = `**⚙️ RelayPlane Status**\n\n`;
  
  if (enabled !== undefined) {
    output += `**Proxy:** ${enabled ? '✅ Running' : '❌ Stopped'}\n`;
  }
  
  if (uptimeMs) {
    const hours = Math.floor(uptimeMs / 3600000);
    const mins = Math.floor((uptimeMs % 3600000) / 60000);
    output += `**Uptime:** ${hours}h ${mins}m\n`;
  }
  
  if (mode) {
    output += `**Mode:** ${mode}\n`;
  }
  
  if (telemetry_enabled !== undefined) {
    output += `**Telemetry:** ${telemetry_enabled ? '✅ Enabled' : '❌ Disabled'}\n`;
  }
  
  if (device_id) {
    output += `**Device ID:** ${device_id.slice(0, 8)}...${device_id.slice(-4)}\n`;
  }

  output += `\n**Dashboard:** ${DASHBOARD_URL}`;
  
  return output;
}

async function handleTelemetry(args) {
  const subcommand = args[0];
  
  if (hasProxyCli()) {
    const output = runProxyCli(['telemetry', subcommand || 'status']);
    return output.trim();
  }
  
  // Fallback guidance
  switch (subcommand) {
    case 'on':
      return `To enable telemetry, run:\n\`relayplane-proxy telemetry on\``;
    case 'off':
      return `To disable telemetry, run:\n\`relayplane-proxy telemetry off\``;
    default:
      return `**Telemetry Control**\n\n` +
        `Check status: \`relayplane-proxy telemetry status\`\n` +
        `Disable: \`relayplane-proxy telemetry off\`\n` +
        `Enable: \`relayplane-proxy telemetry on\`\n\n` +
        `Or run proxy with flags:\n` +
        `• \`--offline\` — No telemetry transmission\n` +
        `• \`--audit\` — See telemetry before sending`;
  }
}

function showDashboard() {
  // Try to get URL from CLI
  if (hasRelayplaneCli()) {
    try {
      const output = runRelayplane(['dashboard', '--url']);
      if (output.includes('http')) {
        return `**🖥️ RelayPlane Dashboard**\n\n${output.trim()}`;
      }
    } catch {
      // Fall through to default
    }
  }
  
  return `**🖥️ RelayPlane Dashboard**\n\n` +
    `${DASHBOARD_URL}\n\n` +
    `View your:\n` +
    `• Usage analytics and cost savings\n` +
    `• Routing decisions and model performance\n` +
    `• Team settings and billing\n\n` +
    `_Sign up for free trial at relayplane.com/trial_`;
}

function listModels() {
  return `**Available Routing Modes**\n\n` +
    `| Mode | Model Alias | Description |\n` +
    `|------|-------------|-------------|\n` +
    `| auto | \`rp:auto\` | Smart routing based on task complexity |\n` +
    `| cost | \`rp:cost\` | Always use cheapest model |\n` +
    `| fast | \`rp:fast\` | Lowest latency model |\n` +
    `| quality | \`rp:best\` | Best quality model (Claude Sonnet 4) |\n` +
    `| balanced | \`rp:balanced\` | Balance of cost and quality |\n\n` +
    `**Usage:** Set model to \`rp:auto\` or \`relayplane:auto\` in your API calls.\n\n` +
    `Configure via dashboard or \`relayplane proxy start\``;
}

async function handleDoctor(args) {
  const isJson = args.includes('--json');
  
  if (hasRelayplaneCli()) {
    try {
      const cmdArgs = ['doctor'];
      if (isJson) cmdArgs.push('--json');
      const output = runRelayplane(cmdArgs);
      return output.trim();
    } catch (error) {
      return `❌ Doctor command failed: ${error.message}`;
    }
  }
  
  // Manual diagnostic checks
  let output = `**🩺 RelayPlane Diagnostics**\n\n`;
  
  // Check API keys
  const anthropicKey = process.env.ANTHROPIC_API_KEY;
  const openaiKey = process.env.OPENAI_API_KEY;
  
  if (anthropicKey) {
    output += `✓ Anthropic API Key: Configured (${anthropicKey.slice(0, 12)}...)\n`;
  } else {
    output += `⚠ Anthropic API Key: Not set\n`;
  }
  
  if (openaiKey) {
    output += `✓ OpenAI API Key: Configured\n`;
  } else {
    output += `○ OpenAI API Key: Not set (optional)\n`;
  }
  
  // Check proxy CLI
  if (hasProxyCli()) {
    output += `✓ Proxy CLI: Installed\n`;
  } else {
    output += `⚠ Proxy CLI: Not installed\n`;
    output += `  Install with: npm install -g @relayplane/proxy\n`;
  }
  
  // Check if proxy is running
  try {
    await callProxy('/health');
    output += `✓ Proxy: Running on ${PROXY_URL}\n`;
  } catch {
    output += `○ Proxy: Not running\n`;
    output += `  Start with: relayplane proxy start\n`;
  }
  
  return output;
}

async function handleProxy(args) {
  const subcommand = args[0] || 'status';
  
  if (hasRelayplaneCli()) {
    try {
      const output = runRelayplane(['proxy', subcommand, ...args.slice(1)]);
      return output.trim();
    } catch (error) {
      return `❌ Proxy command failed: ${error.message}`;
    }
  }
  
  // Fallback guidance
  switch (subcommand) {
    case 'start':
      return `**Start Proxy**\n\n` +
        `\`\`\`bash\n` +
        `# Using relayplane CLI\n` +
        `relayplane proxy start\n\n` +
        `# Or directly\n` +
        `relayplane-proxy --port 3001\n\n` +
        `# With npx\n` +
        `npx @relayplane/proxy\n` +
        `\`\`\``;
    case 'stop':
      return `**Stop Proxy**\n\n` +
        `\`relayplane proxy stop\`\n\n` +
        `Or press Ctrl+C in the terminal running the proxy.`;
    case 'status':
    default:
      try {
        const health = await callProxy('/health');
        return `**Proxy Status: Running**\n\n` +
          `URL: ${PROXY_URL}\n` +
          `Health: OK`;
      } catch {
        return `**Proxy Status: Not Running**\n\n` +
          `Start with: \`relayplane proxy start\``;
      }
  }
}

async function main() {
  const args = process.argv.slice(2);
  
  if (args.length === 0) {
    console.log(`**RelayPlane Commands**\n\n` +
      `• \`/relayplane stats\` — Usage statistics\n` +
      `• \`/relayplane status\` — Proxy health\n` +
      `• \`/relayplane doctor\` — Diagnose issues\n` +
      `• \`/relayplane proxy [start|stop|status]\` — Manage proxy\n` +
      `• \`/relayplane telemetry [on|off]\` — Telemetry control\n` +
      `• \`/relayplane dashboard\` — Cloud dashboard\n` +
      `• \`/relayplane models\` — Routing modes`);
    return;
  }

  const command = args[0];
  
  try {
    switch (command) {
      case 'stats':
        if (hasProxyCli()) {
          const output = runProxyCli(['stats']);
          console.log(output.trim());
        } else if (hasRelayplaneCli()) {
          const output = runRelayplane(['stats']);
          console.log(output.trim());
        } else {
          const stats = await callProxy('/stats');
          console.log(formatStats(stats));
        }
        break;
        
      case 'status':
        if (hasProxyCli()) {
          const output = runProxyCli(['config']);
          console.log(output.trim());
        } else {
          const health = await callProxy('/health');
          console.log(formatStatus(health));
        }
        break;
      
      case 'doctor':
        console.log(await handleDoctor(args.slice(1)));
        break;
      
      case 'proxy':
        console.log(await handleProxy(args.slice(1)));
        break;
        
      case 'telemetry':
        console.log(await handleTelemetry(args.slice(1)));
        break;
        
      case 'dashboard':
        console.log(showDashboard());
        break;
        
      case 'models':
        console.log(listModels());
        break;
        
      // Legacy command - redirect
      case 'switch':
        console.log(`Mode switching moved to dashboard.\n\n` +
          `Visit: ${DASHBOARD_URL}\n\n` +
          `Or use model aliases: \`rp:auto\`, \`rp:cost\`, \`rp:best\``);
        break;
        
      default:
        console.log(`Unknown command: ${command}\n\n` +
          `Available: stats, status, doctor, proxy, telemetry, dashboard, models`);
    }
  } catch (error) {
    console.log(`❌ ${error.message}\n\n` +
      `Make sure the proxy is running:\n` +
      `\`relayplane proxy start\` or \`npx @relayplane/proxy\``);
  }
}

main().catch(console.error);
