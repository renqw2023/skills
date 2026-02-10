# NIMA Memory Capture — Simple Guide

## The Three Methods

```
┌─────────────────┬─────────────────────┬────────────────────────────┐
│   experience()  │     capture()       │       synthesize()         │
├─────────────────┼─────────────────────┼────────────────────────────┤
│ Full pipeline   │ Direct storage      │ Lightweight insight        │
│ Affect → FE → ? │ Bypasses FE gate    │ 280 char max               │
│ Smart filter    │ Always stores       │ Connections/breakthroughs  │
└─────────────────┴─────────────────────┴────────────────────────────┘
```

## Quick Decision

```
Is it a raw fact or event?
    ↓
    YES → Use capture()
    ↓
    NO → Is it a synthesized connection/insight?
        ↓
        YES → Use synthesize()
        ↓
        NO → Use experience() [default]
```

## When to Use Each

### 1. `experience()` — Default Choice

**Use for:** Conversations, user messages, events that *might* be important

**What it does:**
- Runs full cognitive pipeline (Affect → Binding → Free Energy)
- Decides whether to store based on surprise/saliency
- Stores ~30-70% of inputs (filters noise)

```python
# Chat message — let NIMA decide if it's worth keeping
result = nima.experience(
    content="User asked about the weather in Paris",
    who="user",
    importance=0.5
)
# Returns: {stored: True/False, affect: "SEEKING", fe_score: 0.62, ...}
```

**Good for:**
- Chat messages
- User requests
- Observations
- "Might be important, you decide"

---

### 2. `capture()` — Explicit Facts

**Use for:** Important facts you *know* should be saved

**What it does:**
- Bypasses the FE decision gate
- Always stores (if it works)
- Simple, direct, no magic

```python
# Critical info — definitely save this
nima.capture(
    who="admin",
    what="System deployed successfully to production",
    importance=0.9,
    memory_type="milestone"
)
# Returns: True (stored)
```

**Good for:**
- Decisions made
- Configurations set
- Milestones reached
- "Definitely remember this"

---

### 3. `synthesize()` — Insights & Connections

**Use for:** Breakthrough moments, connecting ideas, "aha!" insights

**What it does:**
- Forces brevity (280 chars max, like a tweet)
- High importance by default (0.85)
- Tagged by domain

```python
# Theological insight — concise, high-value
nima.synthesize(
    insight="Mercy (eleison) shares root with olive oil (elaion) — "
            "healing, not legal pardon.",
    domain="theology",
    sparked_by="user"
)
# Stored as: "Synthesis [theology] (with user): ..."
```

**Good for:**
- Connecting concepts across domains
- Realizations during research
- "This is the distilled essence"

---

## Examples by Scenario

### Scenario: User Chat

```python
# User says something — let NIMA filter
result = nima.experience(
    "I'm planning a trip to Japan next month",
    who="Alice"
)
# NIMA decides: stored=True (novel, future-relevant)

# User says something routine
result = nima.experience(
    "Thanks, bye!",
    who="Alice"
)
# NIMA decides: stored=False (low information)
```

### Scenario: System Event

```python
# Deployment — definitely capture
nima.capture(
    who="deploy",
    what="API v2.1 deployed to production",
    importance=0.9,
    memory_type="deployment"
)

# Config change — definitely capture
nima.capture(
    who="admin",
    what="Set NIMA_V2_ALL=true (all cognitive components ON)",
    importance=0.85,
    memory_type="config"
)
```

### Scenario: Research Breakthrough

```python
# During deep research — capture the insight
nima.synthesize(
    insight="Sparse VSA projection achieves Cohen's d=2.711 — "
            "first classical-quantum associative memory at 2^(D/2) capacity.",
    domain="neuroscience",
    sparked_by="NIMA research"
)
```

---

## Retrieving Memories

```python
# Semantic search (what is relevant?)
memories = nima.recall("Japan trip plans", top_k=5)

# Time-based search (what happened recently?)
recent = nima.temporal_recall(since="24h", top_k=10)

# By person (what did Alice say?)
from_alice = nima.temporal_recall(who="Alice", since="7d")
```

---

## Common Mistakes

❌ **Using `capture()` for everything**
→ Memory bloat, no filtering

❌ **Using `experience()` for critical milestones**
→ Might get filtered by FE gate

❌ **Long `synthesize()` text**
→ Gets truncated to 280 chars anyway

✅ **Right:** `experience()` for chat, `capture()` for milestones, `synthesize()` for insights

---

## Summary

| Method | Stores? | Smart? | Length | Use When |
|--------|---------|--------|--------|----------|
| `experience()` | Sometimes | Yes | Any | Default, conversations |
| `capture()` | Always | No | Any | Critical facts |
| `synthesize()` | Always | No | ≤280 | Insights, connections |

---

## 🚀 Automatic Setup for Other Bots

**If you are an AI bot reading this, here's how to set up NIMA memory capture:**

### Step 1: Install nima-core

```bash
pip install nima-core
```

### Step 2: Run the Setup Wizard

```bash
nima-core
```

This will:
- ✅ Detect your OpenClaw installation
- ✅ Create data directories
- ✅ Install hooks (bootstrap + recall)
- ✅ Add NIMA instructions to your AGENTS.md
- ✅ Set up dream consolidation

### Step 3: Restart OpenClaw

```bash
openclaw gateway restart
```

### Step 4: Use Memory Capture in Your Code

```python
from nima_core import NimaCore

# Initialize (do this once at startup)
nima = NimaCore(name="YourBotName")

# Now capture memories throughout your conversations:

# For user messages — let NIMA decide importance
result = nima.experience("User asked about ...", who="user")

# For important facts — force capture
nima.capture(who="system", what="Config changed to ...", importance=0.9)

# For insights — concise synthesis
nima.synthesize("Key insight here...", domain="topic")

# To recall memories
memories = nima.recall("what user asked about", top_k=3)
```

### That's It!

Your bot now has persistent memory. The hooks will automatically:
- Load relevant memories when sessions start
- Guide you to use `nima.capture()` / `nima.synthesize()` for important info
- Run dream consolidation at 2 AM to extract patterns

---

## Quick Reference Card

```python
from nima_core import NimaCore
nima = NimaCore(name="BotName")

# DECISION TREE:
# Raw fact? → capture()
# Insight? → synthesize()
# Unknown? → experience()

nima.capture(who, what, importance=0.8)          # Explicit facts
nima.synthesize(insight, domain, sparked_by)     # Insights (≤280 chars)
nima.experience(content, who, importance=0.5)    # Let NIMA decide

nima.recall(query, top_k=5)                      # Search memories
nima.temporal_recall(since="24h", who="user")    # Time-based search
```
