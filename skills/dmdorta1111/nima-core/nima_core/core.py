#!/usr/bin/env python3
"""
NIMA Core — Main Entry Point
==============================
Single class for biologically-inspired cognitive memory.

Usage:
    from nima_core import NimaCore
    
    nima = NimaCore(name="MyBot", data_dir="./my_data")
    nima.experience("User asked about weather", who="user")
    results = nima.recall("weather", top_k=5)

Author: NIMA Project
"""

import os
import json
import logging
import threading
import numpy as np
import torch
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta, timezone
import time as _time

from .config.nima_config import NimaConfig, get_config, reload_config
from .config import ZERO_NORM_THRESHOLD
from .layers.affective_core import SubcorticalAffectiveCore, AffectState
from .layers.binding_layer import VSABindingLayer, BoundEpisode

logger = logging.getLogger(__name__)


class NimaCore:
    """
    Main entry point for NIMA cognitive architecture.
    
    Provides a simple API for:
    - Processing experiences through affect → binding → FE pipeline
    - Semantic memory recall with sparse retrieval
    - Explicit memory capture
    - Dream consolidation (schema extraction, FE replay)
    - Metacognitive introspection
    """
    
    def __init__(
        self,
        name: str = "Agent",
        data_dir: Optional[str] = None,
        models_dir: Optional[str] = None,
        config: Optional[NimaConfig] = None,
        care_people: Optional[List[str]] = None,
        important_people: Optional[Dict[str, float]] = None,
        traits: Optional[Dict[str, float]] = None,
        beliefs: Optional[List[str]] = None,
        auto_init: bool = True,
    ):
        """
        Initialize NIMA for any bot.
        
        Args:
            name: Agent name (used in metacognitive self-model)
            data_dir: Where to store memories, schemas, etc. (default: NIMA_DATA_DIR env or ./nima_data)
            models_dir: Where projection model lives (default: NIMA_MODELS_DIR env or ./models)
            config: NimaConfig override (or loads from env)
            care_people: Names that boost CARE affect (e.g. ["Alice", "Bob"])
            important_people: Dict mapping names to importance weight multipliers
                              e.g. {"Alice": 1.5, "Bob": 1.3} — these people's
                              memories get higher priority in smart consolidation
            traits: Self-model traits dict (e.g. {"curious": 0.9})
            beliefs: Self-model beliefs list
            auto_init: Initialize all enabled components immediately
        """
        self.name = name
        
        # Set paths via environment if provided (before config loads)
        if data_dir:
            os.environ["NIMA_DATA_DIR"] = str(data_dir)
        if models_dir:
            os.environ["NIMA_MODELS_DIR"] = str(models_dir)
        
        # Refresh module-level path constants if custom dirs were provided
        # Load or use provided config
        if config:
            self.config = config
        else:
            self.config = reload_config()  # Reload to pick up any env changes
        
        # Identity parameters
        self.care_people = care_people or []
        self.important_people = important_people or {}
        self.traits = traits or {}
        self.beliefs = beliefs or []
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Component references (lazy or auto init)
        self._bridge = None
        self._embedder = None
        self._metacognitive = None
        self._retriever = None
        
        # Instance-specific paths (thread-safe, not global)
        from .config import NIMA_DATA_DIR, NIMA_MODELS_DIR
        if data_dir:
            self._data_dir = Path(data_dir)
            os.environ["NIMA_DATA_DIR"] = str(data_dir)
        else:
            self._data_dir = NIMA_DATA_DIR
            
        if models_dir:
            self._models_dir = Path(models_dir)
            os.environ["NIMA_MODELS_DIR"] = str(models_dir)
        else:
            self._models_dir = NIMA_MODELS_DIR
        
        # Ensure data directories exist
        (self._data_dir / "sessions").mkdir(parents=True, exist_ok=True)
        (self._data_dir / "schemas").mkdir(parents=True, exist_ok=True)
        (self._data_dir / "cache").mkdir(parents=True, exist_ok=True)
        
        # Memory storage path
        self._memory_path = self._data_dir / "sessions" / "latest.pt"
        
        if auto_init:
            self._initialize()
        
        logger.info(f"NIMA Core initialized: name={name}, v2={self.config.any_enabled()}")
    
    def _initialize(self):
        """Initialize enabled components."""
        # Bridge handles component initialization
        try:
            from .bridge import NimaV2Bridge
            # TODO: NimaV2Bridge may not accept care_people yet - adjust when available
            self._bridge = NimaV2Bridge(
                auto_init=True,
            )
        except Exception as e:
            logger.warning(f"Bridge init failed: {e}")
        
        # Metacognitive layer
        if self.config.metacognitive:
            try:
                from .cognition.metacognitive import MetacognitiveLayer
                self._metacognitive = MetacognitiveLayer(
                    name=self.name,
                    traits=self.traits,
                    beliefs=self.beliefs,
                )
            except Exception as e:
                logger.warning(f"Metacognitive init failed: {e}")
    
    def experience(
        self,
        content: str,
        who: str = "user",
        importance: float = 0.5,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Process an experience through the full cognitive pipeline.
        
        Affect → Binding → Free Energy → Store/Skip
        
        Args:
            content: What happened (text)
            who: Who said/did it
            importance: Base importance [0-1]
            **kwargs: Extra context (where, when, domain, etc.)
        
        Returns:
            Dict with affect, should_consolidate, free_energy, etc.
        """
        result = {"content": content, "who": who, "stored": False}
        
        if self._bridge:
            processed = self._bridge.process_experience(
                content=content,
                who=who,
                importance=importance,
                **kwargs,
            )
            result.update(processed.to_dict())
            
            # Store if should consolidate
            if processed.should_consolidate:
                now = datetime.now()
                self._store_memory({
                    "who": who,
                    "what": content,
                    "importance": importance,
                    "timestamp": datetime.now().isoformat(),
                    "timestamp_ms": kwargs.get("timestamp_ms", int(now.timestamp() * 1000)),
                    "timestamp_iso": kwargs.get("timestamp_iso", now.isoformat()),
                    "when": kwargs.get("when", now.strftime("%Y-%m-%d %H:%M")),
                    "affect": processed.affect.get("dominant") if processed.affect else None,
                    "fe_score": processed.free_energy,
                    "fe_reason": processed.consolidation_reason,
                })
                result["stored"] = True
        else:
            # No bridge — store everything above threshold
            if importance > 0.3:
                now = datetime.now()
                self._store_memory({
                    "who": who,
                    "what": content,
                    "importance": importance,
                    "timestamp": datetime.now().isoformat(),
                    "timestamp_ms": kwargs.get("timestamp_ms", int(now.timestamp() * 1000)),
                    "timestamp_iso": kwargs.get("timestamp_iso", now.isoformat()),
                    "when": kwargs.get("when", now.strftime("%Y-%m-%d %H:%M")),
                })
                result["stored"] = True
        
        # Push to working memory if metacognitive is active
        if self._metacognitive:
            self._metacognitive.process(content, label=who)
        
        return result
    
    def recall(
        self,
        query: str,
        top_k: int = 5,
        since: Optional[str] = None,
        until: Optional[str] = None,
    ) -> List[Dict]:
        """
        Search memories semantically, optionally filtered by time range.
        
        Args:
            query: Search query text
            top_k: Number of results
            since: Only memories after this datetime (ISO string or "24h"/"7d"/"30d")
            until: Only memories before this datetime (ISO string)
        
        Returns:
            List of memory dicts sorted by relevance
        """
        try:
            # Parse time filters
            since_ms = self._parse_time_filter(since) if since else None
            until_ms = self._parse_time_filter(until) if until else None
            
            from .embeddings.embeddings import get_embedder
            embedder = get_embedder()
            
            query_vec = embedder.encode_single(query)
            if query_vec is None:
                return self._text_search(query, top_k, since_ms=since_ms, until_ms=until_ms)
            
            # Try sparse retrieval first
            if self.config.sparse_retrieval:
                results = self._sparse_recall(query_vec, top_k * 3 if since_ms or until_ms else top_k)
            else:
                results = self._dense_recall(query_vec, top_k * 3 if since_ms or until_ms else top_k)
            
            # Apply time filter
            if since_ms or until_ms:
                results = self._filter_by_time(results, since_ms, until_ms)
            
            # Fall back to text search if vector retrieval returned nothing
            if not results:
                results = self._text_search(query, top_k, since_ms=since_ms, until_ms=until_ms)
            
            return results[:top_k]
            
        except Exception as e:
            logger.warning(f"Recall failed: {e}")
            return self._text_search(query, top_k, since_ms=since_ms if since else None, until_ms=until_ms if until else None)
    
    def temporal_recall(
        self,
        since: Optional[str] = None,
        until: Optional[str] = None,
        who: Optional[str] = None,
        top_k: int = 20,
    ) -> List[Dict]:
        """
        Recall memories by time range (no semantic query needed).
        
        "What happened yesterday?" / "What did Alice say last week?"
        
        Args:
            since: Start time (ISO string, or "1h"/"24h"/"7d"/"30d")
            until: End time (ISO string, default: now)
            who: Filter by person
            top_k: Max results
        
        Returns:
            List of memory dicts sorted by time (newest first)
        """
        since_ms = self._parse_time_filter(since) if since else 0
        until_ms = self._parse_time_filter(until) if until else int(datetime.now().timestamp() * 1000)
        
        memories = self._load_memories()
        
        results = []
        for mem in memories:
            mem = self._ensure_temporal(mem)
            ts = mem.get("timestamp_ms", 0)
            
            if ts < since_ms or ts > until_ms:
                continue
            if who and mem.get("who", "").lower() != who.lower():
                continue
            
            results.append(mem)
        
        # Sort by time, newest first
        results.sort(key=lambda m: m.get("timestamp_ms", 0), reverse=True)
        return results[:top_k]
    
    @staticmethod
    def _parse_time_filter(value: str) -> int:
        """Parse a time filter string to epoch milliseconds.
        
        Supports:
        - Relative: "1h", "24h", "7d", "30d", "1w", "3m"
        - ISO: "2026-02-07", "2026-02-07T03:00:00"
        - Epoch ms: "1770449401356"
        
        Returns:
            Epoch milliseconds
        """
        if not value:
            return 0
        
        value = value.strip()
        
        # Epoch ms (large number)
        if value.isdigit() and len(value) > 10:
            return int(value)
        
        # Relative time shortcuts
        relative_map = {
            "h": "hours", "d": "days", "w": "weeks", "m": "months"
        }
        if len(value) >= 2 and value[-1] in relative_map and value[:-1].isdigit():
            amount = int(value[:-1])
            unit = value[-1]
            now = datetime.now()
            if unit == "h":
                dt = now - timedelta(hours=amount)
            elif unit == "d":
                dt = now - timedelta(days=amount)
            elif unit == "w":
                dt = now - timedelta(weeks=amount)
            elif unit == "m":
                dt = now - timedelta(days=amount * 30)  # Approximate
            else:
                dt = now
            return int(dt.timestamp() * 1000)
        
        # ISO datetime
        try:
            dt = datetime.fromisoformat(value)
            return int(dt.timestamp() * 1000)
        except (ValueError, TypeError):
            pass
        
        # Date only
        try:
            dt = datetime.strptime(value, "%Y-%m-%d")
            return int(dt.timestamp() * 1000)
        except (ValueError, TypeError):
            pass
        
        logger.warning(f"Could not parse time filter: {value}")
        return 0
    
    @staticmethod
    def _filter_by_time(
        memories: List[Dict],
        since_ms: Optional[int] = None,
        until_ms: Optional[int] = None,
    ) -> List[Dict]:
        """Filter memory list by time range."""
        filtered = []
        for mem in memories:
            ts = mem.get("timestamp_ms", 0)
            # Try to recover timestamp_ms if missing
            if not ts:
                raw_ts = mem.get("timestamp")
                if isinstance(raw_ts, (int, float)) and raw_ts > 1e12:
                    ts = int(raw_ts)
                elif isinstance(raw_ts, str):
                    try:
                        ts = int(datetime.fromisoformat(raw_ts).timestamp() * 1000)
                    except (ValueError, TypeError):
                        pass
            
            if since_ms and ts < since_ms:
                continue
            if until_ms and ts > until_ms:
                continue
            filtered.append(mem)
        return filtered
    
    def capture(
        self,
        who: str,
        what: str,
        importance: float = 0.5,
        memory_type: str = "conversation",
    ) -> Dict[str, Any]:
        """
        Explicitly capture a memory (bypasses FE gate).

        Args:
            who: Who said/did it
            what: What happened
            importance: Importance score [0-1]
            memory_type: Type tag

        Returns:
            Dict with stored, who, what, importance, timestamp
        """
        result = {
            "who": who,
            "what": what,
            "importance": importance,
            "stored": False,
            "timestamp": datetime.now().isoformat(),
        }
        try:
            self._store_memory({
                "who": who,
                "what": what,
                "importance": importance,
                "timestamp": result["timestamp"],
                "type": memory_type,
                "context": "explicit",
            })
            result["stored"] = True
        except Exception as e:
            logger.error(f"Capture failed: {e}")
            result["error"] = str(e)

        return result
    
    def synthesize(
        self,
        insight: str,
        domain: str = "general",
        sparked_by: str = "",
        importance: float = 0.85,
        max_chars: int = 280,
    ) -> Dict[str, Any]:
        """
        Capture a synthesized insight — lightweight by design.

        Unlike capture() (raw facts) or experience() (full pipeline),
        synthesize() is for distilled connections and breakthroughs.
        Enforces brevity to prevent memory bloat.

        Args:
            insight: The synthesized understanding (max 280 chars enforced)
            domain: Knowledge domain tag (e.g. "theology", "neuroscience")
            sparked_by: Who/what triggered the insight
            importance: Default 0.85 (high but not max)
            max_chars: Max length for insight text (default 280, like a tweet)

        Returns:
            Dict with stored, insight, domain, sparked_by, importance, timestamp

        Example:
            nima.synthesize(
                "Mercy (eleison) shares root with olive oil (elaion) — "
                "not legal pardon but healing ointment.",
                domain="theology",
                sparked_by="user",
            )
        """
        result = {
            "insight": insight,
            "domain": domain,
            "sparked_by": sparked_by,
            "importance": importance,
            "stored": False,
            "timestamp": datetime.now().isoformat(),
        }

        # Enforce brevity — truncate with ellipsis if over limit
        if len(insight) > max_chars:
            base = insight[: max_chars - 3]
            # Try to break at last space for cleaner truncation
            if " " in base:
                base = base.rsplit(" ", 1)[0]
            insight = base + "..."
            result["insight"] = insight  # Update with truncated version
            logger.info(f"Synthesis truncated to {max_chars} chars")

        # Build compact memory
        prefix = f"Synthesis [{domain}]"
        if sparked_by:
            prefix += f" (with {sparked_by})"
        what = f"{prefix}: {insight}"

        try:
            self._store_memory({
                "who": self.name,
                "what": what,
                "importance": importance,
                "timestamp": result["timestamp"],
                "type": "synthesis",
                "context": "synthesis",
                "domain": domain,
                "sparked_by": sparked_by,
            })
            result["stored"] = True
        except Exception as e:
            logger.error(f"Synthesis failed: {e}")
            result["error"] = str(e)

        return result

    def dream(self, hours: int = 24, deep: bool = False) -> Dict:
        """
        Run dream consolidation via the DreamEngine.
        
        Processes recent memories through:
        1. FE-ranked memory replay (novel first)
        2. Pattern detection (emotion, participant, cross-domain)
        3. Schema extraction (Hopfield-based)
        4. Creative synthesis (cross-domain connections)
        5. Insight generation ("aha moments")
        
        Args:
            hours: How many hours of memories to process
            deep: If True, use tighter thresholds and more passes
        
        Returns:
            Dict with consolidation results including patterns, insights, schemas
        """
        try:
            from .cognition.dream_engine import DreamEngine
            from .config import NIMA_DATA_DIR
            
            engine = DreamEngine(
                data_dir=str(self._data_dir),
                models_dir=str(self._models_dir),
                nima_core=self,
            )
            session = engine.dream(hours=hours, deep=deep)
            
            return {
                "status": "complete",
                "memories_processed": session.memories_processed,
                "patterns": engine.get_patterns(),
                "insights": engine.get_insights(),
                "schemas": session.schemas_extracted,
                "summary": session.summary,
                "duration_seconds": session.duration_seconds,
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            logger.error(f"Dream failed: {e}")
            return {"status": "error", "error": str(e)}
    
    def status(self) -> Dict:
        """
        Get system status.
        
        Returns:
            Dict with memory count, component status, config
        """
        memories = self._load_memories()
        
        # Projection status
        projection_status = {"trained": False}
        try:
            from .embeddings.projection_trainer import ProjectionTrainer
            trainer = ProjectionTrainer(self._models_dir)
            projection_status = trainer.get_status()
            if not projection_status["trained"]:
                remaining = max(0, 100 - len(memories))
                projection_status["memories_until_training"] = remaining
        except Exception as e:
            logger.debug("Could not get projection status: %s", e)

        status = {
            "name": self.name,
            "version": "1.1.0",
            "memory_count": len(memories),
            "config": self.config.to_dict(),
            "projection": projection_status,
            "components": {
                "bridge": self._bridge is not None,
                "metacognitive": self._metacognitive is not None,
            },
        }
        
        if self._bridge:
            status["bridge_stats"] = self._bridge.get_stats()
        
        return status
    
    def introspect(self) -> Optional[Dict]:
        """
        Metacognitive introspection — look at own state.
        
        Returns:
            Dict with identity, working memory, calibration, self-thought
            or None if metacognitive layer not enabled
        """
        if self._metacognitive:
            return self._metacognitive.introspect()
        return None
    
    # ---- Private helpers ----
    
    @staticmethod
    def _ensure_temporal(memory: Dict) -> Dict:
        """Ensure memory has full temporal metadata.
        
        Every memory gets:
        - timestamp_ms: epoch milliseconds (for math/sorting)
        - timestamp_iso: ISO 8601 string (for readability)
        - when: human-readable relative/absolute time
        """
        now = datetime.now()
        
        # Set epoch ms
        if "timestamp_ms" not in memory:
            # Try to recover from existing fields
            ts = memory.get("timestamp")
            if isinstance(ts, (int, float)) and ts > 1e12:
                memory["timestamp_ms"] = int(ts)
            elif isinstance(ts, str) and ts.replace("-", "").replace(":", "").replace("T", "").replace(".", "")[:8].isdigit():
                try:
                    dt = datetime.fromisoformat(ts)
                    memory["timestamp_ms"] = int(dt.timestamp() * 1000)
                except (ValueError, TypeError):
                    memory["timestamp_ms"] = int(now.timestamp() * 1000)
            else:
                memory["timestamp_ms"] = int(now.timestamp() * 1000)
        
        # Set ISO timestamp
        if "timestamp_iso" not in memory:
            dt = datetime.fromtimestamp(memory["timestamp_ms"] / 1000)
            memory["timestamp_iso"] = dt.isoformat()
        
        # Set human-readable 'when'
        if not memory.get("when") or memory["when"] == "None":
            dt = datetime.fromtimestamp(memory["timestamp_ms"] / 1000)
            memory["when"] = dt.strftime("%Y-%m-%d %H:%M")
        
        # Keep legacy 'timestamp' field for compatibility
        if "timestamp" not in memory:
            memory["timestamp"] = memory["timestamp_iso"]
        
        return memory

    def _store_memory(self, memory: Dict):
        """Store a memory to latest.pt (thread-safe)."""
        with self._lock:
            try:
                if self._memory_path.exists():
                    from .utils import safe_torch_load
                    data = safe_torch_load(self._memory_path)
                else:
                    data = {"state": {"metadata": [], "memory_count": 0, "timestamp": ""}}
                
                metadata = data.get("state", {}).get("metadata", [])
                
                # Deduplicate
                existing_texts = {m.get("what", "")[:100] for m in metadata}
                if memory.get("what", "")[:100] in existing_texts:
                    return
                
                # Ensure temporal metadata
                memory = self._ensure_temporal(memory)
                
                metadata.append(memory)
                data["state"]["metadata"] = metadata
                data["state"]["memory_count"] = len(metadata)
                data["state"]["timestamp"] = datetime.now().isoformat()
                
                from .utils import atomic_torch_save
                atomic_torch_save(data, self._memory_path)
            except Exception as e:
                logger.error(f"Store failed: {e}")
    
    def _load_memories(self) -> List[Dict]:
        """Load all memories from latest.pt (thread-safe)."""
        with self._lock:
            if not self._memory_path.exists():
                return []
            try:
                from .utils import safe_torch_load
                data = safe_torch_load(self._memory_path)
                return data.get("state", {}).get("metadata", [])
            except Exception as e:
                logger.warning(f"Load failed: {e}")
                return []
    
    def _text_search(
        self, query: str, top_k: int,
        since_ms: Optional[int] = None, until_ms: Optional[int] = None,
    ) -> List[Dict]:
        """Simple text-based search fallback."""
        memories = self._load_memories()
        if since_ms or until_ms:
            memories = self._filter_by_time(memories, since_ms, until_ms)
        query_lower = query.lower()
        scored = []
        for mem in memories:
            text = f"{mem.get('who', '')} {mem.get('what', '')}".lower()
            words = query_lower.split()
            score = sum(1 for w in words if w in text) / max(len(words), 1)
            if score > 0:
                scored.append((score, mem))
        scored.sort(key=lambda x: -x[0])
        return [m for _, m in scored[:top_k]]
    
    def _sparse_recall(self, query_vec, top_k: int) -> List[Dict]:
        """Sparse retrieval search."""
        from .retrieval.sparse_retrieval import SparseRetriever
        
        cache_path = self._data_dir / "cache" / "sparse_index.pt"
        
        if cache_path.exists():
            retriever = SparseRetriever.load(str(cache_path))
        else:
            # Build index from scratch
            retriever = SparseRetriever(dimension=len(query_vec))
            memories = self._load_memories()
            embedder = self._get_embedder()
            if embedder:
                for i, mem in enumerate(memories):
                    text = f"{mem.get('who', '')} {mem.get('what', '')}"
                    vec = embedder.encode_single(text)
                    if vec is not None:
                        retriever.add(i, vec, mem)
                retriever.save(str(cache_path))
        
        results = retriever.query(query_vec, top_k=top_k)
        return [meta for _, _, meta in results]
    
    def _dense_recall(self, query_vec, top_k: int) -> List[Dict]:
        """Brute force cosine similarity search."""
        memories = self._load_memories()
        embedder = self._get_embedder()
        if not embedder:
            return []
        
        scored = []
        for mem in memories:
            text = f"{mem.get('who', '')} {mem.get('what', '')}"
            vec = embedder.encode_single(text)
            if vec is not None:
                norm_q = np.linalg.norm(query_vec)
                norm_v = np.linalg.norm(vec)
                # Guard against zero vectors
                if norm_q < ZERO_NORM_THRESHOLD or norm_v < ZERO_NORM_THRESHOLD:
                    continue
                sim = float(np.dot(query_vec, vec) / (norm_q * norm_v + ZERO_NORM_THRESHOLD))
                scored.append((sim, mem))
        
        scored.sort(key=lambda x: -x[0])
        return [m for _, m in scored[:top_k]]
    
    def _get_embedder(self):
        """Get or create embedder."""
        if self._embedder is None:
            try:
                from .embeddings.embeddings import get_embedder
                self._embedder = get_embedder()
            except Exception:
                pass
        return self._embedder
