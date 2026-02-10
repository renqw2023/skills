---
name: skillbench
description: Track skill versions, benchmark performance, compare improvements, and get self-improvement signals. Integrates with tasktime and ClawVault.
metadata:
  openclaw:
    requires:
      bins: [skillbench]
    install:
      - id: node
        kind: node
        package: "@versatly/skillbench"
        bins: [skillbench]
        label: Install SkillBench CLI (npm)
---

# skillbench Skill

**Self-improving skill ecosystem for AI agents.**

Track skill versions, benchmark performance, compare improvements, and get signals on what to fix next.

**Part of the [ClawVault](https://clawvault.dev) ecosystem** | [tasktime](https://clawhub.com/skills/tasktime) | [ClawHub](https://clawhub.com)

## Installation

```bash
npm install -g @versatly/skillbench
```

## The Loop

```
1. Use a skill    → skillbench use github@1.0.0
2. Do the task    → tt start "Create PR" && ... && tt stop
3. Record result  → skillbench record "Create PR" --success
4. Check scores   → skillbench score github
5. Improve skill  → Update skill, bump version
6. Repeat         → Compare v1.0.0 vs v1.1.0
```

## Commands

### Track Skills
```bash
skillbench use github@1.2.0            # Set active skill version
skillbench skills                       # List tracked skills + signals
```

### Record Benchmarks
```bash
# Auto-pulls duration from tasktime
skillbench record "Create PR" --success

# Manual duration
skillbench record "Create PR" --duration 45s --success

# Record failures
skillbench record "Create PR" --fail --error-type "auth-error"
```

### Score & Compare
```bash
skillbench score                        # All skills with grades
skillbench score github                 # Single skill
skillbench compare github@1.0.0 github@1.1.0
```

### Export
```bash
skillbench export --format markdown
skillbench export --format json
```

## Grading System

| Grade | Score | Meaning |
|-------|-------|---------|
| 🏆 A+ | 95-100 | Elite performance |
| ✅ A | 85-94 | Excellent |
| 👍 B | 70-84 | Good |
| ⚠️ C | 50-69 | Needs work |
| ❌ D | <50 | Broken |

Based on: Success Rate (40%), Avg Duration (30%), Consistency (20%), Trend (10%)

## tasktime Integration

When you omit `--duration`, skillbench pulls from [tasktime](https://clawhub.com/skills/tasktime):

```bash
tt start "Create PR" -c git
# ... do work ...
tt stop
skillbench record --success   # Duration auto-pulled
```

## ClawVault Integration

Benchmarks sync to [ClawVault](https://clawvault.dev) automatically.

## Improvement Signals

`skillbench skills` shows:
- ⚠️ **needs work** — Success rate below 70%
- 🕐 **stale** — No benchmarks in 7+ days
- ↘️ **declining** — Getting worse over time

## Related

- [ClawVault](https://clawvault.dev) — Memory system for AI agents
- [tasktime](https://clawhub.com/skills/tasktime) — Task timer CLI
- [ClawHub](https://clawhub.com) — Skill marketplace
