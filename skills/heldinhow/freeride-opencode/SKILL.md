---
name: freeride-opencode
description: Configure and optimize OpenCode Zen free models with smart fallbacks for subtasks, heartbeat, and cron jobs. Use when setting up cost-effective AI model routing with automatic failover between free models.
version: 1.0.0
---

# Freeride OpenCode

Configure OpenCode Zen free models with intelligent fallbacks to optimize costs while maintaining reliability.

## Quick Start

Apply optimal free model configuration:

```json
{
  "agents": {
    "defaults": {
      "model": {
        "primary": "opencode/minimax-m2.1-free",
        "fallbacks": [
          "opencode/kimi-k2.5-free",
          "opencode/glm-4.7-free",
          "opencode/gpt-5-nano"
        ]
      },
      "heartbeat": {
        "model": "opencode/gpt-5-nano"
      },
      "subagents": {
        "model": "opencode/kimi-k2.5-free"
      }
    }
  }
}
```

## Model Selection Guide

See [models.md](models.md) for detailed model comparisons, capabilities, and provider information.

| Task Type | Recommended Model | Rationale |
|-----------|------------------|-----------|
| **Primary/General** | MiniMax M2.1 Free | Best free model capability |
| **Subtasks** | Kimi K2.5 Free | Balanced cost/performance |
| **Heartbeat** | GPT 5 Nano | Fastest and cheapest |
| **Cron Jobs** | Depends on complexity |

### Free Models Available

| Model | ID | Best For |
|-------|-----|----------|
| **MiniMax M2.1 Free** | `opencode/minimax-m2.1-free` | Complex reasoning, coding |
| **Kimi K2.5 Free** | `opencode/kimi-k2.5-free` | General purpose, balance |
| **GLM 4.7 Free** | `opencode/glm-4.7-free` | Multilingual, fallback |
| **GPT 5 Nano** | `opencode/gpt-5-nano` | Simple tasks, high frequency |

## Fallback Strategy

Configure fallbacks in priority order:

```json
"fallbacks": [
  "opencode/kimi-k2.5-free",    // Second best capability
  "opencode/glm-4.7-free",       // Alternative provider
  "opencode/gpt-5-nano"          // Fallback of last resort
]
```

**Fallback triggers:**
- Rate limits exceeded
- Auth failures
- Timeouts
- Provider unavailability

## Per-Task Configuration

### Heartbeat (Every 30 min)

```json
"heartbeat": {
  "every": "30m",
  "model": "opencode/gpt-5-nano"
}
```

Use the cheapest model for frequent, lightweight checks.

### Subtasks/Subagents

```json
"subagents": {
  "model": "opencode/kimi-k2.5-free"
}
```

Good balance for secondary tasks that need reasonable capability.

### Complete Example

```json
{
  "agents": {
    "defaults": {
      "model": {
        "primary": "opencode/minimax-m2.1-free",
        "fallbacks": [
          "opencode/kimi-k2.5-free",
          "opencode/glm-4.7-free",
          "opencode/gpt-5-nano"
        ]
      },
      "models": {
        "opencode/minimax-m2.1-free": { "alias": "MiniMax M2.1" },
        "opencode/kimi-k2.5-free": { "alias": "Kimi K2.5" },
        "opencode/glm-4.7-free": {},
        "opencode/gpt-5-nano": {}
      },
      "heartbeat": {
        "every": "30m",
        "model": "opencode/gpt-5-nano"
      },
      "subagents": {
        "model": "opencode/kimi-k2.5-free"
      }
    }
  }
}
```

## Applying Configuration

Use OpenClaw CLI:

```bash
openclaw config.patch --raw '{
  "agents": {
    "defaults": {
      "model": {
        "primary": "opencode/minimax-m2.1-free",
        "fallbacks": ["opencode/kimi-k2.5-free", "opencode/glm-4.7-free", "opencode/gpt-5-nano"]
      },
      "heartbeat": { "model": "opencode/gpt-5-nano" },
      "subagents": { "model": "opencode/kimi-k2.5-free" }
    }
  }
}'
```

## Best Practices

1. **Always have fallbacks** - Configure at least 2-3 fallback models
2. **Mix providers** - Reduces single-provider risk
3. **Match model to task** - Don't use MiniMax for simple checks
4. **Test fallback order** - Put more capable models first
5. **Monitor usage** - Track which models get used most

## Troubleshooting

**Rate limits still occurring?**
- Add more fallback models
- Consider reducing heartbeat frequency

**Responses too slow?**
- Move GPT 5 Nano higher in fallback chain
- Use simpler model for subtasks

**Model not available?**
- Check model ID format: `opencode/model-id-free`
- Verify model is still free (check [models.md](models.md))

## References

### [models.md](models.md)
Complete reference of all free models with capabilities, providers, performance comparisons, and error handling.

### [templates.md](templates.md)
Ready-to-use configuration templates for different use cases (minimal, complete, cost-optimized, performance-optimized).

### [examples/usage.md](examples/usage.md)
Practical examples showing how to use this skill in real scenarios.
