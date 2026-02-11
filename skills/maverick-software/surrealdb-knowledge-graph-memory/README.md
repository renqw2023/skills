# SurrealDB Memory

Knowledge graph memory system with semantic search, MCP tools, and LLM-powered extraction.

## Features

- 🔍 **Semantic Search** - Vector embeddings with cosine similarity
- 🧠 **MCP Tools** - 4 tools for search, recall, store, stats
- 📊 **Confidence Scoring** - With decay and relationship boosts
- 🔗 **Knowledge Graph** - Facts, entities, and relationships
- 🤖 **LLM Extraction** - Auto-extract facts from memory files

## Quick Start

```bash
# Install SurrealDB
./scripts/install.sh

# Start database
surreal start --user root --pass root file:~/.clawdbot/memory/knowledge.db

# Initialize schema
./scripts/init-db.sh

# Setup Python env
python3 -m venv .venv
source .venv/bin/activate
pip install -r scripts/requirements.txt

# Run extraction
python3 scripts/extract-knowledge.py extract --full
```

## MCP Tools

```bash
# Via mcporter
mcporter call surrealdb-memory.knowledge_stats
mcporter call surrealdb-memory.knowledge_search query="topic" limit:5
mcporter call surrealdb-memory.knowledge_recall query="topic"
mcporter call surrealdb-memory.knowledge_store content="New fact"
```

## Requirements

- Python 3.10+
- SurrealDB 2.0+
- OpenAI API key (for embeddings)

## License

MIT
