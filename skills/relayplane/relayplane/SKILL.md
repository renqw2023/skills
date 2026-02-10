---
name: relayplane
description: RelayPlane proxy control - stats, status, diagnostics, telemetry, and dashboard access
user-invocable: true
homepage: https://relayplane.com
version: 2.1.0
author: Continuum
license: MIT
metadata: { "openclaw": { "emoji": "🚀", "category": "ai-tools", "requires": { "bins": ["node", "npx"] } } }
---

# RelayPlane

**Intelligent AI routing that saves you money.**

Route LLM requests through RelayPlane to automatically use the optimal model for each task.

> ⚠️ **Cost Monitoring Required**
>
> RelayPlane routes requests to LLM providers using your API keys. **This incurs real costs.**
> Use `/relayplane stats` to track usage and savings.

## Slash Commands

| Command | Description |
|---------|-------------|
| `/relayplane stats` | Show usage statistics and cost savings |
| `/relayplane status` | Show proxy health and configuration |
| `/relayplane doctor` | Diagnose configuration and connectivity issues |
| `/relayplane proxy [start\|stop\|status]` | Manage the proxy server |
| `/relayplane telemetry [on\|off\|status]` | Manage telemetry settings |
| `/relayplane dashboard` | Get link to cloud dashboard |
| `/relayplane models` | List available routing modes and aliases |

## Usage

When user invokes `/relayplane <subcommand>`, run:

```bash
node {baseDir}/relayplane.js <subcommand>
```

Examples:
- `/relayplane stats` → `node {baseDir}/relayplane.js stats`
- `/relayplane doctor` → `node {baseDir}/relayplane.js doctor`
- `/relayplane proxy start` → `node {baseDir}/relayplane.js proxy start`
- `/relayplane telemetry off` → `node {baseDir}/relayplane.js telemetry off`

## Quick Start

```bash
# Install CLI globally
npm install -g @relayplane/cli @relayplane/proxy

# Check configuration
relayplane doctor

# Start proxy
relayplane proxy start

# Point your SDKs to the proxy
export ANTHROPIC_BASE_URL=http://localhost:3001
export OPENAI_BASE_URL=http://localhost:3001

# Use routing aliases in your API calls
# model: "rp:auto"     - Smart routing
# model: "rp:cost"     - Cheapest model
# model: "rp:best"     - Best quality
# model: "rp:fast"     - Fastest response
```

## Model Routing Aliases

| Alias | Description |
|-------|-------------|
| `rp:auto` / `relayplane:auto` | Smart routing based on task complexity |
| `rp:cost` / `rp:cheap` | Always cheapest model (GPT-4o-mini) |
| `rp:fast` | Lowest latency (Claude Haiku) |
| `rp:best` / `rp:quality` | Best quality (Claude Sonnet 4) |
| `rp:balanced` | Balance of cost and quality |

## Telemetry Control

RelayPlane collects anonymous usage data to improve routing. You can control this:

```bash
relayplane-proxy telemetry status  # Check current setting
relayplane-proxy telemetry off     # Disable completely
relayplane-proxy telemetry on      # Re-enable

# Or run with flags:
relayplane-proxy --offline   # Disable transmission
relayplane-proxy --audit     # See what's sent before sending
```

**What's collected:** Model used, token counts, latency, task type.
**What's NOT collected:** Prompts, responses, or any message content.

## Pricing

- **Free:** Local-only mode, unlimited requests, no account required
- **Pro:** $29/month - Cloud dashboard, analytics, team features
- **Max:** $99/month - Policies, budget controls, 5 team seats
- **Enterprise:** Custom pricing, SSO, audit logs, self-hosted

Sign up at [relayplane.com/trial](https://relayplane.com/trial)

## More Info

- [Dashboard](https://relayplane.com/dashboard)
- [Documentation](https://relayplane.com/docs)
- [GitHub](https://github.com/RelayPlane)
