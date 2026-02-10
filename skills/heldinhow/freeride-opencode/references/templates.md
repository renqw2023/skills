# Configuration Templates

## Minimal Template (Just Fallbacks)

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
      }
    }
  }
}
```

## Complete Template (All Optimizations)

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

## Cost-Optimized Template (Cheapest First)

```json
{
  "agents": {
    "defaults": {
      "model": {
        "primary": "opencode/gpt-5-nano",
        "fallbacks": [
          "opencode/kimi-k2.5-free",
          "opencode/minimax-m2.1-free",
          "opencode/glm-4.7-free"
        ]
      },
      "heartbeat": {
        "model": "opencode/gpt-5-nano"
      },
      "subagents": {
        "model": "opencode/gpt-5-nano"
      }
    }
  }
}
```

## Performance-Optimized Template (Best First)

```json
{
  "agents": {
    "defaults": {
      "model": {
        "primary": "opencode/minimax-m2.1-free",
        "fallbacks": [
          "opencode/kimi-k2.5-free"
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

## Subagent-Only Template

```json
{
  "agents": {
    "defaults": {
      "subagents": {
        "model": "opencode/kimi-k2.5-free"
      }
    }
  }
}
```

## Cron-Specific Template

```json
{
  "agents": {
    "defaults": {
      "model": {
        "primary": "opencode/gpt-5-nano",
        "fallbacks": [
          "opencode/kimi-k2.5-free"
        ]
      }
    }
  }
}
```

## Applying Templates

### Via CLI

```bash
openclaw config.patch --raw '{
  "agents": {
    "defaults": {
      "model": {
        "primary": "opencode/minimax-m2.1-free",
        "fallbacks": ["opencode/kimi-k2.5-free", "opencode/glm-4.7-free", "opencode/gpt-5-nano"]
      }
    }
  }
}'
```

### Via Gateway API

```bash
openclaw gateway call config.patch --params '{
  "raw": "{\"agents\":{\"defaults\":{\"model\":{\"primary\":\"opencode/minimax-m2.1-free\",\"fallbacks\":[\"opencode/kimi-k2.5-free\",\"opencode/glm-4.7-free\",\"opencode/gpt-5-nano\"]}}}}"
}'
```

### Manual Edit

Edit `~/.openclaw/openclaw.json` directly, then run:

```bash
openclaw gateway restart
```

## Verifying Configuration

After applying:

```bash
# Check model configuration
openclaw config.get | jq '.agents.defaults.model'

# List available models
opencode models | grep -E "opencode/.*-free"

# Test fallback
opencode run "Hello" --model opencode/minimax-m2.1-free
```

## Resetting to Defaults

To remove FreeRide configuration and return to defaults:

```json
{
  "agents": {
    "defaults": {
      "model": {
        "primary": "anthropic/claude-sonnet-4-5"
      }
    }
  }
}
```
