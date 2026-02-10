---
name: muninn
version: 1.6.0
homepage: https://www.muninn.space
description: Universal Context Protocol (CXP) for AI agents. Provides per-project long-term memory, semantic search, and surgical context injection. Features a mandatory 'Brain-First' Gate Keeper (v2.1.4) that prevents hallucinations. Created by @Blackknight1dev.
metadata: {"clawdbot":{"emoji":"🐦⬛","requires":{"bins":["node"]},"install":[{"id":"npm","kind":"node","package":"muninn-core","version":"2.1.4","bins":["muninn-core"],"label":"Install Muninn Core"}]}}
---

# Muninn - The Universal Memory Layer

Muninn is an advanced per-project memory system designed for AI agents. It uses the **Context Exchange Protocol (CXP)** to provide high-performance, token-efficient context management.

## 🛡️ Integration

Muninn operates as an MCP (Model Context Protocol) server. To use this skill, ensure that the `muninn-core` package is installed in your environment.

### 🚀 The Muninn Protocol (v2.1.4 - ENFORCED)

As an agent, you SHOULD follow these three pillars of the Muninn workflow to remain efficient and accurate. Note that the MCP server **blocks** non-exempt tools if `brain_check` hasn't been called first in the current session.

1.  **Orient Yourself (`brain_check`)**: Call this at the start of every session or when switching projects. It loads the project index and identifies key files and patterns.
2.  **Search Before You Code (`search_context`)**: Never assume you know the codebase. Search for existing patterns or prior decisions to avoid duplication and bugs.
3.  **Learn as You Go (`add_memory`)**: Every significant fix, architectural decision, or user preference should be saved as a memory. This ensures persistence across future sessions.

## 🛠 Tool Reference (MCP)

- **`init_project`**: Initialize Muninn in a new project directory.
- **`brain_check`**: MANDATORY first step. Loads context and patterns.
- **`add_memory`**: Persist facts, decisions, and lessons learned.
- **`search_context`**: Semantically search project code and memories.
- **`reindex_context`**: Rebuild the semantic index to reflect file changes.
- **`health_check`**: Verify the status of the Muninn system.

---

## 🦞 Pro-Tip for Agents
Muninn surgically retrieves only what's needed. Instead of reading large files, use `search_context` to find the exact lines that matter. This significantly reduces context window overhead and token costs.
