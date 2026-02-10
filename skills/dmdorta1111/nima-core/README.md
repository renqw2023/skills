<div align="center">

<img src="https://raw.githubusercontent.com/lilubot/nima-core/main/assets/banner.png" alt="NIMA — Noosphere Integrated Memory Architecture" width="100%">

<br>

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![GitHub](https://img.shields.io/badge/GitHub-nima--core-blue?style=flat&logo=github)](https://github.com/lilubot/nima-core)

**Give your AI agent a mind — not just a database.**

[Documentation](#architecture) · [Quick Start](#quick-start) · [API Reference](#api-reference)

</div>

---

NIMA (Noosphere Integrated Memory Architecture) provides emotion-aware memory, principled consolidation, and self-reflective cognition.

## Installation

```bash
pip install nima-core
```

### OpenClaw Integration (Recommended)

One command sets up everything:

```bash
nima-core
```

The wizard automatically:
- ✅ Detects your OpenClaw installation
- ✅ Creates data directories
- ✅ Installs hooks via `openclaw hooks install` (bootstrap + recall)
- ✅ Enables hooks
- ✅ Adds NIMA instructions to your AGENTS.md
- ✅ Guides you through dream consolidation setup

After setup, restart OpenClaw:

```bash
openclaw gateway restart
```

That's it. Your agent now has persistent memory.

### Manual Hook Install

If you prefer manual control:

```bash
# Install hooks from nima-core package
openclaw hooks install /path/to/nima-core

# Enable them
openclaw hooks enable nima-bootstrap
openclaw hooks enable nima-recall

# Restart
openclaw gateway restart
```

### Standalone (No OpenClaw)

```python
from nima_core.config.auto import get_nima_config, setup_paths

config = get_nima_config()  # Auto-detects environment
setup_paths(config)         # Creates directories
```

### How Memory Capture Works

NIMA hooks into OpenClaw at two points:

1. **Bootstrap** (`agent:bootstrap`) — Injects memory status + relevant memories when sessions start
2. **Agent-driven capture** — Your agent calls `nima.capture()` or `nima.experience()` during conversations

> **Note:** OpenClaw does not emit per-message hook events. Real-time capture happens through agent instructions (AGENTS.md), heartbeat polling, or the markdown bridge. See [Heartbeat Service](#heartbeat-service) and [Markdown Bridge](#markdown-bridge--bidirectional-memory-sync).

## Quick Start

```python
from nima_core import NimaCore

# Initialize for your bot
nima = NimaCore(
    name="MyBot",
    data_dir="./my_data",
    care_people=["Alice", "Bob"],  # Names that boost CARE affect
)

# Process an experience
result = nima.experience("User asked about the weather", who="user", importance=0.6)
# → Affect: SEEKING, FE: 0.62, stored: True

# Search memories
memories = nima.recall("weather conversations", top_k=5)

# Explicit capture (bypasses FE gate)
nima.capture("admin", "System deployed successfully", importance=0.9, memory_type="milestone")

# Capture a synthesized insight (lightweight, 280 char max, no bloat)
nima.synthesize(
    "Mercy (eleison) shares root with olive oil (elaion) — healing, not legal pardon.",
    domain="theology",
    sparked_by="Melissa",
)

# Run dream consolidation
nima.dream(hours=24)

# Self-reflection
print(nima.introspect())
```

## Architecture

```
┌─────────────────────────────────────────────────┐
│           METACOGNITIVE (Frontier 9)            │
│  Strange loop · Self-model · 4-chunk WM         │
├─────────────────────────────────────────────────┤
│            SEMANTIC (Frontier 8)                │
│  Hyperbolic embeddings · Concept hierarchies    │
├─────────────────────────────────────────────────┤
│             EPISODIC (Tiers 1-2)                │
│  VSA + Holographic storage · Sparse retrieval   │
├─────────────────────────────────────────────────┤
│          CONSOLIDATION (Tier 2)                 │
│  Free Energy decisions · Schema extraction      │
├─────────────────────────────────────────────────┤
│            BINDING (Layer 2)                    │
│  VSA circular convolution · Phase coherence     │
├─────────────────────────────────────────────────┤
│         AFFECTIVE CORE (Layer 1)                │
│  Panksepp's 7 affects · Somatic markers         │
└─────────────────────────────────────────────────┘
```

**Data flow:**
```
Input → Embed (384D) → Project (50KD) → Affect → Bind → FE Decision → Store/Skip
```

## Configuration

### Feature Flags

All cognitive components are **ON by default** (v1.1.0+). Override with environment variables if needed.

```bash
# Everything is enabled by default — no setup needed!
# To disable the full cognitive stack:
export NIMA_V2_ALL=false

# Or disable individually
export NIMA_V2_AFFECTIVE=true   # Panksepp's 7 affects
export NIMA_V2_BINDING=true     # VSA circular convolution
export NIMA_V2_FE=true          # Free Energy consolidation
export NIMA_V2_EPISODIC=true    # Enhanced episodic storage
export NIMA_V2_SEMANTIC=true    # Poincaré ball hierarchies
export NIMA_V2_META=true        # Self-model + 4-chunk WM

# These are ON by default (validated):
export NIMA_SPARSE_RETRIEVAL=true   # Two-stage sparse index
export NIMA_PROJECTION=true         # 384D → 50KD projection

# Kill switch
export NIMA_V2_DISABLED=true
```

### Paths

| Variable | Default | Description |
|----------|---------|-------------|
| `NIMA_DATA_DIR` | `./nima_data` | Memory storage (sessions, schemas, cache) |
| `NIMA_MODELS_DIR` | `./models` | ML models (projection matrix) |

### Size Limits

| Variable | Default | Description |
|----------|---------|-------------|
| `NIMA_MAX_CACHE` | `10000` | Binding layer filler cache |
| `NIMA_MAX_SEQUENCES` | `1000` | Temporal sequence corpus |
| `NIMA_MAX_FE_HISTORY` | `500` | Free Energy score history |
| `NIMA_MAX_QUESTIONS` | `100` | Active inference questions |
| `NIMA_MAX_ACTIONS` | `200` | Active inference action history |

## API Reference

### NimaCore

```python
nima = NimaCore(
    name="MyBot",              # Agent name (for self-model)
    data_dir="./data",         # Storage path
    models_dir="./models",     # Model files path
    care_people=["Alice"],     # Names that boost CARE affect
    traits={"curious": 0.9},   # Self-model personality traits
    beliefs=["I help people"], # Self-model beliefs
    auto_init=True,            # Init components immediately
)

# Core API
nima.experience(content, who, importance, **kwargs) → Dict
nima.recall(query, top_k=5) → List[Dict]
nima.capture(who, what, importance, memory_type) → bool
nima.synthesize(insight, domain, sparked_by, importance) → bool
nima.dream(hours=24) → Dict
nima.status() → Dict
nima.introspect() → Dict | None
```

### Heartbeat Service

```python
from nima_core.services.heartbeat import NimaHeartbeat

def my_message_source():
    """Return new messages since last check."""
    return [{"who": "user", "what": "hello", "importance": 0.5}]

heartbeat = NimaHeartbeat(
    nima,
    message_source=my_message_source,
    interval_minutes=10,
    consolidation_hour=2,  # Dream at 2 AM
    # Bidirectional markdown sync (optional)
    markdown_dir="./memory/",
    markdown_export_path="./memory/nima_export.md",
    extra_markdown_files=["./MEMORY.md"],
)

heartbeat.start()              # Blocking
# or
heartbeat.start_background()   # Non-blocking thread
```

### Markdown Bridge — Bidirectional Memory Sync

Bridge NIMA's vector store with any text-based memory system (OpenClaw, Obsidian, plain files).

```python
from nima_core import NimaCore, MarkdownBridge

nima = NimaCore(name="MyBot")
bridge = MarkdownBridge(nima, agent_name="MyBot")

# Export NIMA → markdown (for text search / human reading)
bridge.export_to_markdown("./memory/nima_export.md")

# Ingest markdown → NIMA (with deduplication)
bridge.ingest_from_markdown(["./memory/2026-02-06.md", "./MEMORY.md"])

# Ingest entire directory
bridge.ingest_from_directory("./memory/", exclude_patterns=["nima_export"])

# Full bidirectional sync (ingest + export in one call)
result = bridge.sync(
    markdown_dir="./memory/",
    export_path="./memory/nima_export.md",
    extra_files=["./MEMORY.md"],
)
# → {"ingest": {"added": 42, "duplicates": 8}, "export": {"memories_exported": 758}}
```

**Deduplication** uses two stages:
1. MD5 fingerprint (fast exact match)
2. Jaccard word similarity at 0.7 threshold (catches paraphrases)

**Auto-sync via Heartbeat:**
- After each capture: NIMA → markdown export
- During nightly consolidation: markdown → NIMA ingest + export

### Individual Components

```python
# Affective Core — Panksepp's 7 affects
from nima_core.layers.affective_core import SubcorticalAffectiveCore
core = SubcorticalAffectiveCore(care_people=["Alice"])
state = core.process(stimulus, {"text": "I love learning!", "who": "user"})
# state.dominant → "CARE", state.valence → 0.8

# Binding Layer — VSA circular convolution
from nima_core.layers.binding_layer import VSABindingLayer
layer = VSABindingLayer(dimension=10000)
episode = layer.create_episode({"WHO": "Alice", "WHAT": "asked a question"})

# Free Energy — Principled consolidation
from nima_core.cognition.free_energy import FreeEnergyConsolidation
fe = FreeEnergyConsolidation()
result = fe.should_consolidate("novel experience", affect={"valence": 0.7})
# result.should_consolidate → True, result.reason → "high_free_energy"

# Sparse Retrieval — 10-19x speedup
from nima_core.retrieval.sparse_retrieval import SparseRetriever
retriever = SparseRetriever(dimension=50000)
retriever.add(0, embedding, metadata)
results = retriever.query(query_vec, top_k=10)

# Metacognitive — Self-reflection
from nima_core.cognition.metacognitive import MetacognitiveLayer
meta = MetacognitiveLayer(name="MyBot", traits={"curious": 0.9})
intro = meta.introspect()  # identity, working memory, calibration
```

## The 7 Core Affects

| Affect | Valence | Arousal | Description |
|--------|---------|---------|-------------|
| **SEEKING** | +0.6 | 0.7 | Curiosity, anticipation |
| **RAGE** | −0.8 | 0.9 | Frustration, anger |
| **FEAR** | −0.7 | 0.8 | Anxiety, apprehension |
| **LUST** | +0.7 | 0.8 | Desire, attraction |
| **CARE** | +0.8 | 0.4 | Nurturing, love |
| **PANIC** | −0.9 | 0.85 | Separation distress |
| **PLAY** | +0.9 | 0.75 | Joy, excitement |

## Free Energy Consolidation

Replaces arbitrary thresholds with principled Bayesian decisions:

```
F = Prediction Error + 0.3 × Complexity
```

| Decision | Condition | Result |
|----------|-----------|--------|
| High FE | Novel experience | **STORE** |
| Epistemic | Reduces uncertainty | **STORE** |
| Emotional | Strong feeling | **STORE** |
| Novel Pattern | No matching schema | **STORE** |
| Below threshold | Already known | **SKIP** |

## Project Structure

```
nima-core/
├── nima_core/
│   ├── __init__.py          # Package exports
│   ├── core.py              # NimaCore main class
│   ├── bridge.py            # V2 integration bridge
│   ├── config/
│   │   └── nima_config.py   # Feature flags
│   ├── layers/
│   │   ├── affective_core.py  # Panksepp's 7 affects
│   │   └── binding_layer.py   # VSA convolution
│   ├── cognition/
│   │   ├── free_energy.py       # FE consolidation
│   │   ├── schema_extractor.py  # Pattern extraction
│   │   ├── temporal_encoder.py  # Sequence encoding
│   │   ├── sequence_predictor.py
│   │   ├── active_inference.py  # Self-directed learning
│   │   ├── hyperbolic_memory.py # Poincaré ball
│   │   └── metacognitive.py     # Strange loops + WM
│   ├── retrieval/
│   │   ├── sparse_retrieval.py  # Two-stage sparse index
│   │   └── resonator.py        # Factorized decomposition
│   ├── embeddings/
│   │   └── embeddings.py   # Unified embedding pipeline
│   └── services/
│       ├── heartbeat.py     # Background capture
│       └── consolidation.py # Dream consolidation
├── tests/
│   └── test_integration.py
├── setup.py
├── requirements.txt
├── .env.example
├── SKILL.md
└── README.md
```

## Testing

```bash
cd nima-core
python3 tests/test_integration.py
```

## Research Foundation

| Component | Theory | Author |
|-----------|--------|--------|
| Affective Core | 7 Emotional Systems | Jaak Panksepp (1998) |
| Somatic Markers | Somatic Marker Hypothesis | Antonio Damasio |
| VSA Binding | Holographic Reduced Representations | Tony Plate (1995) |
| Free Energy | Free Energy Principle | Karl Friston |
| Sparse VSA | Hyperdimensional Computing | Pentti Kanerva |
| Resonator Networks | Factored Retrieval | Frady & Kleyko (2020) |
| Active Inference | Expected Free Energy | Karl Friston |
| Hyperbolic Embeddings | Poincaré Embeddings | Nickel & Kiela (2017) |
| Strange Loops | Self-Reference | Douglas Hofstadter (1979) |
| Working Memory | 4-Chunk Limit | Nelson Cowan (2001) |

## Authors

**NIMA Project**, February 2026

---

*Built with science. Deployed with love.*