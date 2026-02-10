---
name: nima-bootstrap
description: "Injects NIMA cognitive memory status into session context on bootstrap"
metadata:
  openclaw:
    emoji: "🧠"
    events: ["agent:bootstrap"]
    requires:
      config: ["workspace.dir"]
---

# 🧠 nima-bootstrap

Injects NIMA cognitive memory system status into every session.

## What It Does

On `agent:bootstrap`:
1. Skips subagent and heartbeat sessions
2. Locates nima_core (workspace `nima-core/` or pip-installed)
3. Runs NIMA status check via Python
4. Generates `NIMA_STATUS.md` with memory count and system info
5. Injects into `bootstrapFiles` so the agent knows its memory state

## Requirements

- `workspace.dir` must be configured
- Python 3 with nima-core installed (`pip install nima-core` or local copy)

## Configuration

```json
{
  "hooks": {
    "internal": {
      "entries": {
        "nima-bootstrap": {
          "enabled": true,
          "timeout": 15000
        }
      }
    }
  }
}
```

## Error Handling

- Logs errors but never throws — session continues even if NIMA is unavailable
- Injects error status so the agent knows NIMA isn't working
- 15 second timeout on Python execution
