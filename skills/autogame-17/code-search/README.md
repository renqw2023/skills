# Code Search Skill

Smart repository search tool for OpenClaw agents.
Replaces manual `grep` commands with a safer, context-aware search interface.

## Usage

```bash
# Basic search
node skills/code-search/index.js --query "function main"

# Search specific file types
node skills/code-search/index.js --query "TODO" --include "*.js,*.ts"

# Search with context
node skills/code-search/index.js --query "error" --context 2
```

## Features

- **Smart Filtering**: Automatically ignores `node_modules`, `.git`, `dist`, `build`.
- **Context Awareness**: Shows lines before/after matches.
- **Safety**: Truncates large outputs to prevent token overflow.
- **Structured Output**: Returns JSON or readable text.

