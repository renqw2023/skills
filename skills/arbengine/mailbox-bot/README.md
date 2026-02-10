# mailbox.bot OpenClaw Skill

Physical address infrastructure for AI agents.

## Quick Start: Publishing to ClawHub

### 1. Install ClawHub CLI

```bash
npm install -g clawhub
```

### 2. Authenticate

```bash
clawhub login
```

This opens GitHub OAuth. Your account must be **at least 1 week old** to publish.

### 3. Publish

```bash
clawhub publish . \
  --slug mailbox-bot \
  --name "mailbox.bot" \
  --version 1.0.0 \
  --changelog "Initial release — physical address infrastructure for AI agents. Waitlist signup works now, full API coming soon."
```

### 4. Verify

```bash
clawhub info mailbox-bot
```

## Installation (for OpenClaw users)

```bash
clawhub install mailbox-bot
```

Or paste the skill GitHub URL directly into your OpenClaw chat.

## What This Gets You

**Right now (v1.0):**
- Install count = real signal of interest
- Waitlist signups from agents who actually tried to use it
- Distribution before full product launch

**Later (v2.0+):**
- Update skill with live API endpoints
- Everyone who installed gets notified
- They can upgrade to start using real package data

## Skill Metrics

ClawHub tracks:
- Install count
- Active usage
- Version distribution

This gives you PMF signal **before** you finish building the full product.

## Next Steps

1. Publish to ClawHub today
2. Share in OpenClaw Discord / communities
3. Watch install count
4. Build v1 API while distribution grows
5. Ship v2.0 skill when API is live
6. Everyone who installed gets notified

## Why This Works

- Skills are just markdown files (no complex framework)
- Anyone can install, even if product isn't done
- Waitlist endpoint requires no auth → frictionless
- Install count = validation signal
- You're building audience **before** building product

---

Questions? support@mailbox.bot
