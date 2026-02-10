---
name: nima-recall
description: "Auto-queries NIMA memory and injects relevant memories into session context"
metadata:
  openclaw:
    emoji: "🔮"
    events: ["agent:bootstrap"]
    requires:
      config: ["workspace.dir"]
---

# 🔮 nima-recall

Automatically queries NIMA vector store on session bootstrap and injects relevant memories into context.

## What It Does

On `agent:bootstrap`:
1. Skips subagent and heartbeat sessions
2. Extracts recent conversation context from the session transcript
3. Queries NIMA with semantic search
4. Injects top N relevant memories as `NIMA_RECALL.md` in bootstrapFiles

## Why This Matters

NIMA stores episodic memories, but they're only useful if queried. This hook ensures relevant memories are automatically surfaced when conversations start, providing continuity across sessions.

## Requirements

- `workspace.dir` must be configured
- Python 3 with nima-core installed
- At least one memory stored in NIMA

## Configuration

```json
{
  "hooks": {
    "internal": {
      "entries": {
        "nima-recall": {
          "enabled": true,
          "limit": 3,
          "timeout": 15000
        }
      }
    }
  }
}
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `limit` | number | 3 | Max memories to retrieve |
| `timeout` | number | 15000 | Query timeout in ms |

## Performance

- **First call:** ~6-9 seconds (loading embeddings + building index)
- **Subsequent calls:** <1 second (cached sparse index)

## Error Handling

- Logs errors but never throws — session continues if NIMA is unavailable
- Skips if insufficient conversation context (<20 chars)
