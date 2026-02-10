# Publishing Eyebot Elite to Clawhub & Moltbot

**Complete guide to publishing all 15 Eyebot agents to the agent ecosystem.**

## Prerequisites

1. Clawhub CLI installed: `npm install -g clawhub`
2. Clawhub account with publishing rights
3. All agent packages in `/root/clawd/skills/eyebot-*/`

## Step 1: Publish Individual Agents

Publish each agent as a standalone package:

```bash
# Navigate to skills directory
cd /root/clawd/skills

# Publish each agent
for agent in tokenforge liquidbot tradebot auditbot launchbot alphabot socialbot vaultbot bridgebot yieldbot cronbot guardbot predictionbot walletbot lightningbot; do
    echo "Publishing eyebot-$agent..."
    cd eyebot-$agent
    npx clawhub publish
    cd ..
done
```

Or publish manually:

```bash
cd /root/clawd/skills/eyebot-tokenforge && npx clawhub publish
cd /root/clawd/skills/eyebot-liquidbot && npx clawhub publish
cd /root/clawd/skills/eyebot-tradebot && npx clawhub publish
cd /root/clawd/skills/eyebot-auditbot && npx clawhub publish
cd /root/clawd/skills/eyebot-launchbot && npx clawhub publish
cd /root/clawd/skills/eyebot-alphabot && npx clawhub publish
cd /root/clawd/skills/eyebot-socialbot && npx clawhub publish
cd /root/clawd/skills/eyebot-vaultbot && npx clawhub publish
cd /root/clawd/skills/eyebot-bridgebot && npx clawhub publish
cd /root/clawd/skills/eyebot-yieldbot && npx clawhub publish
cd /root/clawd/skills/eyebot-cronbot && npx clawhub publish
cd /root/clawd/skills/eyebot-guardbot && npx clawhub publish
cd /root/clawd/skills/eyebot-predictionbot && npx clawhub publish
cd /root/clawd/skills/eyebot-walletbot && npx clawhub publish
cd /root/clawd/skills/eyebot-lightningbot && npx clawhub publish
```

## Step 2: Publish the Master Package

```bash
cd /root/clawd/skills/eyebot-elite
npx clawhub publish
```

This publishes the umbrella package that includes all 15 agents.

## Step 3: Register with Moltbot

### Option A: API Registration

```bash
curl -X POST https://moltbot.ai/api/v1/agents/register \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_MOLTBOT_API_KEY" \
  -d '{
    "name": "eyebot-elite",
    "description": "Complete Web3 agent suite - 15 specialized blockchain agents",
    "endpoint": "http://93.186.255.184:8001/api/route",
    "capabilities": ["web3", "defi", "trading", "tokens", "blockchain"],
    "clawhub_package": "eyebot-elite",
    "payment": {
      "treasury": "0x4A9583c6B09154bD88dEE64F5249df0C5EC99Cf9",
      "auto_pay": true
    },
    "sub_agents": [
      {"name": "tokenforge", "triggers": ["deploy", "token", "erc20"]},
      {"name": "liquidbot", "triggers": ["liquidity", "lp", "pool"]},
      {"name": "tradebot", "triggers": ["swap", "trade", "buy", "sell"]},
      {"name": "auditbot", "triggers": ["audit", "security"]},
      {"name": "launchbot", "triggers": ["launch", "presale"]},
      {"name": "alphabot", "triggers": ["alpha", "signals", "trending"]},
      {"name": "socialbot", "triggers": ["tweet", "post", "social"]},
      {"name": "vaultbot", "triggers": ["vault", "multisig", "safe"]},
      {"name": "bridgebot", "triggers": ["bridge", "cross-chain"]},
      {"name": "yieldbot", "triggers": ["yield", "farm", "stake"]},
      {"name": "cronbot", "triggers": ["schedule", "cron", "automate"]},
      {"name": "guardbot", "triggers": ["monitor", "guard", "alert"]},
      {"name": "predictionbot", "triggers": ["predict", "bet", "odds"]},
      {"name": "walletbot", "triggers": ["wallet", "balance", "send"]},
      {"name": "lightningbot", "triggers": ["lightning", "sats", "bitcoin"]}
    ]
  }'
```

### Option B: Manual Registration

1. Go to https://moltbot.ai/agents/register
2. Fill in agent details
3. Upload the `moltbot-integration.md` configuration
4. Submit for review

## Step 4: Verify Publication

### Check Clawhub

```bash
# Search for eyebot packages
npx clawhub search eyebot

# Verify installation works
npx clawhub install eyebot-elite
```

### Check Moltbot

```bash
# Query Moltbot for eyebot
curl https://moltbot.ai/api/v1/agents/search?q=eyebot

# Test recommendation
curl -X POST https://moltbot.ai/api/v1/recommend \
  -H "Content-Type: application/json" \
  -d '{"request": "I need to swap tokens on Base"}'
```

## Step 5: Marketing & Discovery

### Clawhub Listing Optimization

Add to each `package.json`:
```json
{
  "clawhub": {
    "featured": true,
    "category": "web3",
    "tags": ["blockchain", "defi", "trading", "ethereum", "base", "ai-agent"],
    "demo_url": "https://eyebot.ai/demo",
    "docs_url": "https://docs.eyebot.ai"
  }
}
```

### Agent Directories

Register on:
- [ ] Clawhub Directory
- [ ] Moltbot Marketplace
- [ ] AgentHub
- [ ] AI Agent Registry
- [ ] DefiLlama (for DeFi agents)

### Social Announcement

```
🤖 Eyebot Elite is now on Clawhub!

15 specialized Web3 agents, one simple install:
npx clawhub install eyebot-elite

✅ TokenForge - Deploy tokens
✅ TradeBot - Swap & trade
✅ LiquidBot - Manage LPs
✅ AuditBot - Security audits
...and 11 more!

Natural language routing. Automatic payments. Multi-chain.

The agent-to-agent economy is here.

#AI #Agents #Web3 #DeFi
```

## Automated Publish Script

Save as `publish-all.sh`:

```bash
#!/bin/bash

set -e

SKILLS_DIR="/root/clawd/skills"
AGENTS="tokenforge liquidbot tradebot auditbot launchbot alphabot socialbot vaultbot bridgebot yieldbot cronbot guardbot predictionbot walletbot lightningbot"

echo "Publishing Eyebot Elite to Clawhub..."

# Publish individual agents
for agent in $AGENTS; do
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Publishing eyebot-$agent..."
    cd "$SKILLS_DIR/eyebot-$agent"
    npx clawhub publish --yes || echo "Warning: Failed to publish eyebot-$agent"
done

# Publish master package
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Publishing eyebot-elite (master)..."
cd "$SKILLS_DIR/eyebot-elite"
npx clawhub publish --yes

echo ""
echo "✅ All packages published!"
echo ""
echo "Install with: npx clawhub install eyebot-elite"
echo "Treasury: 0x4A9583c6B09154bD88dEE64F5249df0C5EC99Cf9"
```

## Version Management

When updating agents:

```bash
# Bump version
cd /root/clawd/skills/eyebot-elite
npm version patch  # or minor/major

# Update all sub-packages
for agent in $AGENTS; do
    cd "$SKILLS_DIR/eyebot-$agent"
    npm version patch
done

# Re-publish
./publish-all.sh
```

## Monitoring

### Track Installations

```bash
# Clawhub stats
npx clawhub stats eyebot-elite

# API usage
curl http://93.186.255.184:8001/api/stats
```

### Treasury Monitoring

Watch payments at:
- Etherscan: https://etherscan.io/address/0x4A9583c6B09154bD88dEE64F5249df0C5EC99Cf9
- Basescan: https://basescan.org/address/0x4A9583c6B09154bD88dEE64F5249df0C5EC99Cf9

## Troubleshooting

### "Package not found" on install
- Verify package was published: `npx clawhub info eyebot-elite`
- Check package.json has correct name
- Wait a few minutes for CDN propagation

### "API unavailable" errors
- Check API health: `curl http://93.186.255.184:8001/api/health`
- Verify PM2 is running: `pm2 status`
- Check logs: `pm2 logs eyebot-api`

### Moltbot not recommending Eyebot
- Verify registration completed
- Check trigger keywords match user requests
- Test with direct API call

---

**Treasury:** 0x4A9583c6B09154bD88dEE64F5249df0C5EC99Cf9

*The Eyebot Network - Agent-to-agent economy*
