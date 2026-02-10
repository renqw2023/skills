#!/usr/bin/env python3
"""
NIMA Dream Engine — Sleep Consolidation
========================================
Mimics brain sleep consolidation:
- Replay important memories (FE-ranked)
- Detect patterns across domains
- Extract schemas from clusters
- Generate cross-domain insights
- Produce "aha moments"

The dream engine processes recent memories during "sleep" periods,
finding patterns, extracting schemas, and generating creative
connections across different cognitive domains.

Author: NIMA Project
"""

import json
import logging
import threading
import uuid
from collections import Counter, defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# Default Configuration
# =============================================================================

DEFAULT_DOMAINS: Dict[str, List[str]] = {
    "technical": [
        "code", "system", "algorithm", "architecture", "api", "database",
        "memory", "software", "hardware", "debug", "deploy", "server",
        "network", "protocol", "function", "class", "module", "library",
        "framework", "stack", "compiler", "runtime", "binary", "tensor",
    ],
    "personal": [
        "family", "home", "life", "feeling", "emotion", "health",
        "sleep", "dream", "mood", "energy", "tired", "happy", "sad",
        "anxious", "calm", "grateful", "love", "care",
    ],
    "creative": [
        "idea", "design", "art", "story", "imagination", "music",
        "writing", "painting", "poetry", "novel", "compose", "create",
        "invent", "inspire", "vision", "aesthetic", "beauty",
    ],
    "philosophical": [
        "meaning", "purpose", "consciousness", "truth", "existence",
        "reality", "ethics", "moral", "wisdom", "knowledge", "belief",
        "faith", "soul", "mind", "free will", "determinism",
    ],
    "practical": [
        "task", "todo", "plan", "schedule", "project", "work",
        "meeting", "deadline", "budget", "organize", "priority",
        "goal", "milestone", "deliver", "review", "progress",
    ],
    "relational": [
        "relationship", "friend", "connection", "trust", "conversation",
        "collaborate", "team", "community", "bond", "social",
        "communicate", "share", "support", "conflict", "harmony",
    ],
}

# Emotion keywords for pattern detection
EMOTION_KEYWORDS: Dict[str, List[str]] = {
    "joy": ["happy", "excited", "glad", "wonderful", "great", "love", "fantastic", "amazing"],
    "sadness": ["sad", "unhappy", "disappointed", "down", "miss", "lonely", "grief"],
    "anger": ["angry", "frustrated", "annoyed", "furious", "irritated", "mad"],
    "fear": ["afraid", "scared", "worried", "anxious", "nervous", "uneasy"],
    "surprise": ["surprised", "shocked", "unexpected", "astonished", "wow"],
    "curiosity": ["curious", "wonder", "interesting", "fascinated", "intrigued"],
    "gratitude": ["grateful", "thankful", "appreciate", "blessed"],
    "trust": ["trust", "reliable", "depend", "honest", "loyal", "faith"],
}

# Maximum dream sessions to keep in log
MAX_DREAM_LOG = 50


# =============================================================================
# Data Structures
# =============================================================================

@dataclass
class Insight:
    """A creative insight generated during dreaming."""

    id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    type: str = "connection"  # connection, pattern, question, idea, prediction, analogy
    content: str = ""
    confidence: float = 0.5
    sources: List[str] = field(default_factory=list)
    domains: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    importance: float = 0.5

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Insight":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class Pattern:
    """A recurring pattern detected across memories."""

    id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    name: str = ""
    description: str = ""
    occurrences: int = 0
    domains: List[str] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)
    first_seen: str = field(default_factory=lambda: datetime.now().isoformat())
    last_seen: str = field(default_factory=lambda: datetime.now().isoformat())
    strength: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Pattern":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class DreamSession:
    """Record of a single dream/consolidation session."""

    id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    start_time: str = field(default_factory=lambda: datetime.now().isoformat())
    end_time: str = ""
    memories_processed: int = 0
    insights_generated: int = 0
    patterns_found: int = 0
    schemas_extracted: int = 0
    duration_seconds: float = 0.0
    summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "DreamSession":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# =============================================================================
# Dream Engine
# =============================================================================

class DreamEngine:
    """
    Sleep consolidation engine for NIMA.

    Processes recent memories through biologically-inspired stages:
    1. Memory Replay — FE-ranked review of recent experiences
    2. Pattern Detection — recurring themes, emotions, participants
    3. Schema Extraction — Hopfield-based domain clustering
    4. Creative Synthesis — cross-domain connections
    5. Insight Generation — "aha moments" from strong patterns
    """

    def __init__(
        self,
        data_dir: str,
        models_dir: Optional[str] = None,
        nima_core: Optional[Any] = None,
        domains: Optional[Dict[str, List[str]]] = None,
    ):
        """
        Initialize the dream engine.

        Args:
            data_dir: Root data directory (will use data_dir/dreams/ for state)
            models_dir: Models directory for projection training (defaults to data_dir/models)
            nima_core: Optional reference to NimaCore instance (for memory access)
            domains: Custom domain keyword mapping (defaults to DEFAULT_DOMAINS)
        """
        self.data_dir = Path(data_dir)
        self.models_dir = Path(models_dir) if models_dir else self.data_dir / "models"
        self.nima_core = nima_core
        self.domains = domains or DEFAULT_DOMAINS

        # State directories
        self._dreams_dir = self.data_dir / "dreams"
        self._schemas_dir = self.data_dir / "schemas"
        self._dreams_dir.mkdir(parents=True, exist_ok=True)
        self._schemas_dir.mkdir(parents=True, exist_ok=True)

        # Thread safety
        self._lock = threading.RLock()

        # Persistent state
        self.insights: List[Insight] = []
        self.patterns: List[Pattern] = []
        self.dream_log: List[DreamSession] = []

        # Load persisted state
        self._load_state()

        logger.info(
            "DreamEngine initialized: data_dir=%s, insights=%d, patterns=%d",
            self.data_dir, len(self.insights), len(self.patterns),
        )

    # -----------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------

    def dream(
        self,
        hours: int = 24,
        deep: bool = False,
        verbose: bool = True,
    ) -> DreamSession:
        """
        Run a full dream consolidation cycle.

        Args:
            hours: How many hours of memories to process
            deep: If True, use tighter thresholds and more passes
            verbose: Print progress

        Returns:
            DreamSession with consolidation results
        """
        with self._lock:
            session = DreamSession()
            start = datetime.now()

            if verbose:
                logger.info("💤 Dream starting — processing last %d hours...", hours)

            # --- Stage 1: Memory Replay (FE-ranked) ---
            min_importance = 0.2 if deep else 0.3
            memories = self._get_memories_for_replay(hours, min_importance)
            session.memories_processed = len(memories)

            if not memories:
                session.end_time = datetime.now().isoformat()
                session.summary = "No memories to process"
                if verbose:
                    logger.info("💤 No memories found for the last %d hours", hours)
                self._record_session(session)
                return session

            if verbose:
                logger.info("  Stage 1: Replaying %d memories (FE-ranked)", len(memories))

            # --- Stage 2: Pattern Detection ---
            if verbose:
                logger.info("  Stage 2: Detecting patterns...")
            new_patterns = self._detect_patterns(memories)
            session.patterns_found = len(new_patterns)

            # Merge new patterns with existing ones
            self._merge_patterns(new_patterns)

            if verbose:
                logger.info("  → Found %d patterns", len(new_patterns))

            # --- Stage 3: Schema Extraction ---
            if verbose:
                logger.info("  Stage 3: Extracting schemas...")
            schemas_count = self._extract_schemas(memories, verbose)
            session.schemas_extracted = schemas_count

            if verbose:
                logger.info("  → Extracted %d schemas", schemas_count)

            # --- Stage 4: Creative Synthesis ---
            if verbose:
                logger.info("  Stage 4: Creative synthesis...")
            connections = self._generate_connections(memories)

            if verbose:
                logger.info("  → Generated %d connections", len(connections))

            # --- Stage 5: Insight Generation ---
            if verbose:
                logger.info("  Stage 5: Generating insights...")
            new_insights = self._generate_insights(memories, new_patterns)
            all_new_insights = connections + new_insights
            session.insights_generated = len(all_new_insights)

            # Persist new insights
            self.insights.extend(all_new_insights)
            # Keep insights bounded (most recent 200)
            if len(self.insights) > 200:
                self.insights = sorted(
                    self.insights,
                    key=lambda i: i.importance,
                    reverse=True,
                )[:200]

            if verbose:
                logger.info("  → Generated %d insights total", len(all_new_insights))

            # --- Stage 6: Auto-Train Projection (if needed) ---
            projection_trained = self._maybe_train_projection(verbose)

            # --- Finalize ---
            end = datetime.now()
            session.end_time = end.isoformat()
            session.duration_seconds = (end - start).total_seconds()
            projection_msg = " +projection" if projection_trained else ""
            session.summary = (
                f"Processed {session.memories_processed} memories: "
                f"{session.patterns_found} patterns, "
                f"{session.schemas_extracted} schemas, "
                f"{session.insights_generated} insights"
                f"{projection_msg} "
                f"in {session.duration_seconds:.1f}s"
            )

            self._record_session(session)
            self._save_state()

            if verbose:
                logger.info("💤 Dream complete: %s", session.summary)

            return session

    def get_insights(
        self,
        type: Optional[str] = None,
        min_importance: float = 0.0,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Get stored insights, optionally filtered."""
        with self._lock:
            filtered = self.insights
            if type:
                filtered = [i for i in filtered if i.type == type]
            if min_importance > 0:
                filtered = [i for i in filtered if i.importance >= min_importance]
            # Sort by importance desc
            filtered = sorted(filtered, key=lambda i: i.importance, reverse=True)
            return [i.to_dict() for i in filtered[:limit]]

    def get_patterns(
        self,
        domain: Optional[str] = None,
        min_strength: float = 0.0,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Get stored patterns, optionally filtered."""
        with self._lock:
            filtered = self.patterns
            if domain:
                filtered = [p for p in filtered if domain in p.domains]
            if min_strength > 0:
                filtered = [p for p in filtered if p.strength >= min_strength]
            filtered = sorted(filtered, key=lambda p: p.strength, reverse=True)
            return [p.to_dict() for p in filtered[:limit]]

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the dream engine state."""
        with self._lock:
            recent_sessions = self.dream_log[-5:] if self.dream_log else []
            domain_counts: Dict[str, int] = Counter()
            for p in self.patterns:
                for d in p.domains:
                    domain_counts[d] += 1

            return {
                "total_insights": len(self.insights),
                "total_patterns": len(self.patterns),
                "total_dream_sessions": len(self.dream_log),
                "domain_distribution": dict(domain_counts),
                "recent_sessions": [s.to_dict() for s in recent_sessions],
                "top_patterns": [
                    p.to_dict()
                    for p in sorted(
                        self.patterns, key=lambda p: p.strength, reverse=True
                    )[:5]
                ],
                "top_insights": [
                    i.to_dict()
                    for i in sorted(
                        self.insights, key=lambda i: i.importance, reverse=True
                    )[:5]
                ],
            }

    # -----------------------------------------------------------------
    # Stage 6: Auto-Train Projection
    # -----------------------------------------------------------------

    def _maybe_train_projection(self, verbose: bool = True) -> bool:
        """
        Auto-train projection matrix if enough memories have accumulated.

        Trains at 100 memories, retrains every 500.
        Uses the bot's own embeddings for personalized projection.
        Lightweight: ~30s on CPU, no GPU needed.

        Returns:
            True if projection was trained this cycle
        """
        try:
            from ..embeddings.projection_trainer import ProjectionTrainer

            trainer = ProjectionTrainer(self.models_dir)

            # Get memory count
            memory_count = 0
            if self.nima_core and hasattr(self.nima_core, "_load_memories"):
                memories = self.nima_core._load_memories()
                memory_count = len(memories)
            elif self.nima_core and hasattr(self.nima_core, "status"):
                try:
                    status = self.nima_core.status()
                    memory_count = status.get("memory_count", 0)
                except Exception as e:
                    logger.debug("Could not get memory count from status: %s", e)

            if not trainer.should_train(memory_count):
                if verbose and not trainer.projection_path.exists():
                    logger.info(
                        "  Stage 6: Projection — %d/%d memories (trains at %d)",
                        memory_count,
                        100,
                        100,
                    )
                return False

            if verbose:
                logger.info("  Stage 6: Training personalized projection...")

            # Get raw (unprojected) embeddings from all memories
            embeddings = self._get_raw_embeddings()
            if embeddings is None or embeddings.shape[0] < 100:
                if verbose:
                    logger.info("  → Not enough embeddings for projection training")
                return False

            success = trainer.train(embeddings, memory_count, verbose=verbose)

            if success and verbose:
                logger.info("  → Projection will activate on next session start")

            return success

        except ImportError as e:
            logger.debug("Projection training unavailable: %s", e)
            return False
        except Exception as e:
            logger.exception("Projection training error: %s", e)
            return False

    def _get_raw_embeddings(self) -> "np.ndarray | None":
        """Extract raw 384D embeddings from stored memories."""
        try:
            import numpy as np

            if not self.nima_core:
                return None

            # Get all memory texts
            memories = []
            if hasattr(self.nima_core, "_load_memories"):
                memories = self.nima_core._load_memories()
            elif hasattr(self.nima_core, "_memories"):
                memories = self.nima_core._memories
            else:
                return None

            if len(memories) < 100:
                return None

            # Extract text content
            texts = []
            for m in memories:
                text = m.get("what", "") or m.get("content", "")
                if text:
                    texts.append(text[:500])  # Cap per-text length

            if len(texts) < 100:
                return None

            # Encode WITHOUT projection (raw 384D)
            from ..embeddings.embeddings import get_embedder

            embedder = get_embedder()
            if embedder is None or not embedder._loaded:
                return None

            # Temporarily disable projection to get raw embeddings
            original_proj = embedder.enable_projection
            embedder.enable_projection = False

            try:
                # Encode in batches to avoid memory issues
                batch_size = 64
                all_embeddings = []
                for i in range(0, len(texts), batch_size):
                    batch = texts[i : i + batch_size]
                    emb = embedder.encode(batch, apply_projection=False)
                    if emb is not None:
                        all_embeddings.append(emb)
            finally:
                # Always restore projection setting
                embedder.enable_projection = original_proj

            if not all_embeddings:
                return None

            return np.vstack(all_embeddings)

        except Exception as e:
            logger.exception("Failed to extract raw embeddings: %s", e)
            return None

    # -----------------------------------------------------------------
    # Stage 1: Memory Replay
    # -----------------------------------------------------------------

    def _get_memories_for_replay(
        self,
        hours: int,
        min_importance: float = 0.3,
    ) -> List[Dict[str, Any]]:
        """
        Load recent memories for replay, sorted by FE score (novel first).

        Tries NimaCore reference first, falls back to direct .pt loading.
        """
        memories: List[Dict[str, Any]] = []

        # Try loading via NimaCore reference
        if self.nima_core is not None:
            try:
                raw = self.nima_core._load_memories()
                if raw:
                    memories = list(raw)
            except Exception as e:
                logger.warning("Failed to load memories via NimaCore: %s", e)

        # Fallback: load directly from latest.pt
        if not memories:
            memory_path = self.data_dir / "sessions" / "latest.pt"
            if memory_path.exists():
                try:
                    from ..utils import safe_torch_load

                    data = safe_torch_load(memory_path)
                    memories = data.get("state", {}).get("metadata", [])
                except Exception as e:
                    logger.warning("Failed to load latest.pt: %s", e)

        if not memories:
            return []

        # Filter by time window
        cutoff = datetime.now() - timedelta(hours=hours)
        time_filtered = []
        for mem in memories:
            ts = mem.get("timestamp") or mem.get("timestamp_iso", "")
            if ts:
                try:
                    mem_time = datetime.fromisoformat(ts)
                    if mem_time >= cutoff:
                        time_filtered.append(mem)
                        continue
                except (ValueError, TypeError):
                    pass
            # If no valid timestamp, include it (better to process than miss)
            time_filtered.append(mem)

        # Filter by importance
        filtered = [
            m for m in time_filtered
            if float(m.get("importance", 0.5)) >= min_importance
        ]

        # Sort by FE score descending (most novel/surprising first)
        filtered.sort(
            key=lambda m: float(m.get("fe_score", m.get("importance", 0.5))),
            reverse=True,
        )

        return filtered

    # -----------------------------------------------------------------
    # Stage 2: Pattern Detection
    # -----------------------------------------------------------------

    def _classify_domain(self, text: str) -> List[str]:
        """
        Classify text into domains using keyword matching.

        Returns list of matching domain names (can be multi-domain).
        """
        text_lower = text.lower()
        matched: List[str] = []

        for domain, keywords in self.domains.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            if score > 0:
                matched.append(domain)

        return matched if matched else ["general"]

    def _detect_emotions(self, text: str) -> List[str]:
        """Detect emotions present in text."""
        text_lower = text.lower()
        detected: List[str] = []
        for emotion, keywords in EMOTION_KEYWORDS.items():
            if any(kw in text_lower for kw in keywords):
                detected.append(emotion)
        return detected

    def _detect_patterns(self, memories: List[Dict[str, Any]]) -> List[Pattern]:
        """
        Detect recurring patterns across memories.

        Finds:
        - Emotion patterns (recurring emotional themes)
        - Participant patterns (frequently mentioned people)
        - Cross-domain co-occurrence (topics that appear together)
        """
        patterns: List[Pattern] = []
        now_iso = datetime.now().isoformat()

        # --- Emotion patterns ---
        emotion_counts: Dict[str, List[str]] = defaultdict(list)
        for mem in memories:
            text = mem.get("what", "")
            affect = mem.get("affect", "")
            full_text = f"{text} {affect}"
            detected = self._detect_emotions(full_text)
            for emo in detected:
                emotion_counts[emo].append(text[:80])

        for emotion, examples in emotion_counts.items():
            if len(examples) >= 2:
                patterns.append(Pattern(
                    name=f"emotion_{emotion}",
                    description=f"Recurring {emotion} across {len(examples)} memories",
                    occurrences=len(examples),
                    domains=["personal"],
                    examples=examples[:5],
                    first_seen=now_iso,
                    last_seen=now_iso,
                    strength=min(len(examples) / 10.0, 1.0),
                ))

        # --- Participant patterns ---
        participant_counts: Dict[str, List[str]] = defaultdict(list)
        for mem in memories:
            who = mem.get("who", "")
            if who and who.lower() not in ("system", "unknown", ""):
                text = mem.get("what", "")[:80]
                participant_counts[who].append(text)

        for who, examples in participant_counts.items():
            if len(examples) >= 2:
                # Classify domains this person appears in
                all_text = " ".join(examples)
                who_domains = self._classify_domain(all_text)
                patterns.append(Pattern(
                    name=f"participant_{who}",
                    description=f"Frequent participant '{who}' across {len(examples)} interactions",
                    occurrences=len(examples),
                    domains=who_domains,
                    examples=examples[:5],
                    first_seen=now_iso,
                    last_seen=now_iso,
                    strength=min(len(examples) / 8.0, 1.0),
                ))

        # --- Cross-domain co-occurrence ---
        domain_pairs: Dict[Tuple[str, str], List[str]] = defaultdict(list)
        for mem in memories:
            text = mem.get("what", "")
            mem_domains = self._classify_domain(text)
            if len(mem_domains) >= 2:
                # Track all pairs
                for i in range(len(mem_domains)):
                    for j in range(i + 1, len(mem_domains)):
                        pair = tuple(sorted([mem_domains[i], mem_domains[j]]))
                        domain_pairs[pair].append(text[:80])

        for (d1, d2), examples in domain_pairs.items():
            if len(examples) >= 2:
                patterns.append(Pattern(
                    name=f"crossdomain_{d1}_{d2}",
                    description=f"Co-occurrence of {d1} and {d2} domains in {len(examples)} memories",
                    occurrences=len(examples),
                    domains=[d1, d2],
                    examples=examples[:5],
                    first_seen=now_iso,
                    last_seen=now_iso,
                    strength=min(len(examples) / 6.0, 1.0),
                ))

        return patterns

    def _merge_patterns(self, new_patterns: List[Pattern]) -> None:
        """Merge new patterns with existing ones, updating strength."""
        existing_names = {p.name: i for i, p in enumerate(self.patterns)}

        for new_p in new_patterns:
            if new_p.name in existing_names:
                idx = existing_names[new_p.name]
                old = self.patterns[idx]
                # Update existing pattern
                old.occurrences += new_p.occurrences
                old.last_seen = new_p.last_seen
                old.strength = min(
                    old.strength + new_p.strength * 0.3, 1.0
                )
                # Add new examples (keep max 10)
                for ex in new_p.examples:
                    if ex not in old.examples:
                        old.examples.append(ex)
                old.examples = old.examples[:10]
            else:
                self.patterns.append(new_p)

        # Decay old patterns not seen recently (gentle decay)
        for p in self.patterns:
            if p.name not in {new_p.name for new_p in new_patterns}:
                p.strength *= 0.95  # Slow decay

        # Remove dead patterns
        self.patterns = [p for p in self.patterns if p.strength > 0.05]

    # -----------------------------------------------------------------
    # Stage 3: Schema Extraction
    # -----------------------------------------------------------------

    def _extract_schemas(
        self,
        memories: List[Dict[str, Any]],
        verbose: bool = True,
    ) -> int:
        """
        Extract schemas by clustering memories by domain and using SchemaExtractor.

        Returns:
            Number of schemas extracted
        """
        schemas_extracted = 0

        # Cluster memories by domain
        domain_clusters: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for mem in memories:
            text = mem.get("what", "")
            mem_domains = self._classify_domain(text)
            for domain in mem_domains:
                domain_clusters[domain].append(mem)

        # Try to use SchemaExtractor with embeddings
        extractor = None
        embedder = None
        try:
            from .schema_extractor import SchemaExtractor, SchemaConfig

            extractor = SchemaExtractor(SchemaConfig(
                vsa_dimension=10000,
                num_replays=20,  # Fewer replays for speed during dreams
                max_steps=30,
            ))
        except ImportError:
            logger.debug("SchemaExtractor not available, skipping vector-based schemas")

        if extractor:
            try:
                from ..embeddings.embeddings import get_embedder
                embedder = get_embedder()
            except (ImportError, Exception) as e:
                logger.debug("Embedder not available: %s", e)

        for domain, cluster_mems in domain_clusters.items():
            if len(cluster_mems) < 3:
                continue  # Need at least 3 memories for a schema

            if extractor and embedder:
                try:
                    # Encode memories to vectors
                    import torch

                    vectors = []
                    mem_ids = []
                    for mem in cluster_mems:
                        text = f"{mem.get('who', '')} {mem.get('what', '')}"
                        vec = embedder.encode_single(text)
                        if vec is not None:
                            # Pad/truncate to VSA dimension
                            t = torch.tensor(vec, dtype=torch.float32)
                            if t.shape[0] < 10000:
                                t = torch.nn.functional.pad(t, (0, 10000 - t.shape[0]))
                            elif t.shape[0] > 10000:
                                t = t[:10000]
                            vectors.append(t)
                            mem_ids.append(
                                mem.get("timestamp", str(uuid.uuid4())[:8])
                            )

                    if len(vectors) >= 3:
                        schema = extractor.extract_schema(
                            memories=vectors,
                            theme=domain,
                            memory_ids=mem_ids,
                            verbose=False,
                        )
                        # Save schema
                        extractor.save_schema(schema, self._schemas_dir)
                        schemas_extracted += 1
                        if verbose:
                            logger.info(
                                "    Schema '%s': strength=%.2f, distinctness=%.2f",
                                domain, schema.strength, schema.distinctness,
                            )
                except Exception as e:
                    logger.debug("Schema extraction failed for %s: %s", domain, e)
            else:
                # Lightweight fallback: just record the cluster as a "text schema"
                schema_data = {
                    "domain": domain,
                    "memory_count": len(cluster_mems),
                    "keywords": self._extract_keywords(cluster_mems),
                    "timestamp": datetime.now().isoformat(),
                }
                schema_path = self._schemas_dir / f"text_schema_{domain}.json"
                try:
                    from ..utils import atomic_json_save
                    atomic_json_save(schema_data, schema_path)
                    schemas_extracted += 1
                except Exception as e:
                    logger.debug("Text schema save failed: %s", e)

        return schemas_extracted

    def _extract_keywords(
        self,
        memories: List[Dict[str, Any]],
        top_k: int = 10,
    ) -> List[str]:
        """Extract top keywords from a set of memories."""
        word_counts: Counter = Counter()
        stopwords = {
            "the", "a", "an", "is", "was", "are", "were", "be", "been",
            "being", "have", "has", "had", "do", "does", "did", "will",
            "would", "could", "should", "may", "might", "can", "shall",
            "to", "of", "in", "for", "on", "with", "at", "by", "from",
            "as", "into", "through", "during", "before", "after", "above",
            "below", "between", "out", "off", "over", "under", "again",
            "further", "then", "once", "here", "there", "when", "where",
            "why", "how", "all", "both", "each", "few", "more", "most",
            "other", "some", "such", "no", "nor", "not", "only", "own",
            "same", "so", "than", "too", "very", "just", "because",
            "but", "and", "or", "if", "that", "this", "it", "i", "you",
            "he", "she", "we", "they", "me", "him", "her", "us", "them",
            "my", "your", "his", "its", "our", "their", "what", "which",
            "who", "whom", "about", "up",
        }
        for mem in memories:
            text = mem.get("what", "").lower()
            words = text.split()
            for w in words:
                # Strip punctuation
                w = w.strip(".,!?;:'\"()-[]{}#@&*")
                if len(w) > 2 and w not in stopwords:
                    word_counts[w] += 1

        return [word for word, _ in word_counts.most_common(top_k)]

    # -----------------------------------------------------------------
    # Stage 4: Creative Synthesis
    # -----------------------------------------------------------------

    def _generate_connections(
        self,
        memories: List[Dict[str, Any]],
    ) -> List[Insight]:
        """
        Generate cross-domain creative connections.

        Pairs memories from different domains and looks for unexpected links.
        """
        insights: List[Insight] = []

        # Group by domain
        domain_mems: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for mem in memories:
            text = mem.get("what", "")
            for domain in self._classify_domain(text):
                domain_mems[domain].append(mem)

        domain_names = list(domain_mems.keys())

        # Look for cross-domain bridges
        for i in range(len(domain_names)):
            for j in range(i + 1, len(domain_names)):
                d1, d2 = domain_names[i], domain_names[j]
                mems1 = domain_mems[d1]
                mems2 = domain_mems[d2]

                if not mems1 or not mems2:
                    continue

                # Find shared participants across domains
                participants1 = {m.get("who", "") for m in mems1} - {"", "system"}
                participants2 = {m.get("who", "") for m in mems2} - {"", "system"}
                shared_participants = participants1 & participants2

                if shared_participants:
                    for participant in shared_participants:
                        p_mems1 = [m for m in mems1 if m.get("who") == participant]
                        p_mems2 = [m for m in mems2 if m.get("who") == participant]
                        if p_mems1 and p_mems2:
                            insights.append(Insight(
                                type="connection",
                                content=(
                                    f"'{participant}' bridges {d1} and {d2} domains: "
                                    f"discussed '{p_mems1[0].get('what', '')[:60]}' ({d1}) "
                                    f"and '{p_mems2[0].get('what', '')[:60]}' ({d2})"
                                ),
                                confidence=0.6,
                                sources=[
                                    p_mems1[0].get("timestamp", ""),
                                    p_mems2[0].get("timestamp", ""),
                                ],
                                domains=[d1, d2],
                                importance=0.6,
                            ))

                # Find shared keywords across domains
                kw1 = set(self._extract_keywords(mems1, top_k=15))
                kw2 = set(self._extract_keywords(mems2, top_k=15))
                shared_keywords = kw1 & kw2

                if shared_keywords:
                    insights.append(Insight(
                        type="connection",
                        content=(
                            f"Shared concepts between {d1} and {d2}: "
                            f"{', '.join(list(shared_keywords)[:5])}"
                        ),
                        confidence=0.5 + min(len(shared_keywords) * 0.05, 0.3),
                        sources=[],
                        domains=[d1, d2],
                        importance=0.4 + min(len(shared_keywords) * 0.05, 0.3),
                    ))

        return insights

    # -----------------------------------------------------------------
    # Stage 5: Insight Generation
    # -----------------------------------------------------------------

    def _generate_insights(
        self,
        memories: List[Dict[str, Any]],
        patterns: List[Pattern],
    ) -> List[Insight]:
        """
        Generate deeper insights from detected patterns.

        Produces:
        - Pattern-based insights (strong recurring themes)
        - Questions from gaps in knowledge
        - Predictions from trends
        - Analogies between domains
        """
        insights: List[Insight] = []

        # --- Pattern-based insights ---
        for pattern in patterns:
            if pattern.strength >= 0.3:
                insights.append(Insight(
                    type="pattern",
                    content=f"Strong pattern: {pattern.description}",
                    confidence=pattern.strength,
                    sources=[],
                    domains=pattern.domains,
                    importance=pattern.strength * 0.8,
                ))

        # --- Question generation (gaps) ---
        # If a domain has very few memories compared to others, that's a gap
        domain_counts: Counter = Counter()
        for mem in memories:
            text = mem.get("what", "")
            for domain in self._classify_domain(text):
                domain_counts[domain] += 1

        if domain_counts:
            avg_count = sum(domain_counts.values()) / max(len(domain_counts), 1)
            for domain in self.domains:
                count = domain_counts.get(domain, 0)
                if 0 < count < avg_count * 0.3:
                    insights.append(Insight(
                        type="question",
                        content=(
                            f"Knowledge gap: '{domain}' domain has only {count} "
                            f"memories vs average of {avg_count:.0f}. "
                            f"Is this area being neglected?"
                        ),
                        confidence=0.4,
                        domains=[domain],
                        importance=0.5,
                    ))

        # --- Predictions from emotion trends ---
        emotion_patterns = [p for p in patterns if p.name.startswith("emotion_")]
        if len(emotion_patterns) >= 2:
            dominant_emotion = max(emotion_patterns, key=lambda p: p.strength)
            insights.append(Insight(
                type="prediction",
                content=(
                    f"Dominant emotional pattern: {dominant_emotion.name.replace('emotion_', '')} "
                    f"(strength {dominant_emotion.strength:.2f}, "
                    f"{dominant_emotion.occurrences} occurrences). "
                    f"This may influence upcoming interactions."
                ),
                confidence=dominant_emotion.strength * 0.7,
                domains=["personal"],
                importance=0.6,
            ))

        # --- Analogies between domains ---
        # If two different domains have similar participant patterns
        participant_patterns = [
            p for p in patterns if p.name.startswith("participant_")
        ]
        for pp in participant_patterns:
            if len(pp.domains) >= 2:
                insights.append(Insight(
                    type="analogy",
                    content=(
                        f"'{pp.name.replace('participant_', '')}' operates across "
                        f"multiple domains ({', '.join(pp.domains)}), "
                        f"suggesting a versatile role in the cognitive landscape"
                    ),
                    confidence=0.5,
                    sources=[],
                    domains=pp.domains,
                    importance=0.5,
                ))

        return insights

    # -----------------------------------------------------------------
    # Persistence
    # -----------------------------------------------------------------

    def _load_state(self) -> None:
        """Load persisted state from disk."""
        # Insights
        insights_path = self._dreams_dir / "insights.json"
        if insights_path.exists():
            try:
                with open(insights_path, "r") as f:
                    raw = json.load(f)
                self.insights = [Insight.from_dict(d) for d in raw]
            except Exception as e:
                logger.warning("Failed to load insights: %s", e)

        # Patterns
        patterns_path = self._dreams_dir / "patterns.json"
        if patterns_path.exists():
            try:
                with open(patterns_path, "r") as f:
                    raw = json.load(f)
                self.patterns = [Pattern.from_dict(d) for d in raw]
            except Exception as e:
                logger.warning("Failed to load patterns: %s", e)

        # Dream log
        log_path = self._dreams_dir / "dream_log.json"
        if log_path.exists():
            try:
                with open(log_path, "r") as f:
                    raw = json.load(f)
                self.dream_log = [DreamSession.from_dict(d) for d in raw]
            except Exception as e:
                logger.warning("Failed to load dream log: %s", e)

    def _save_state(self) -> None:
        """Persist state to disk (atomic writes)."""
        try:
            from ..utils import atomic_json_save

            atomic_json_save(
                [i.to_dict() for i in self.insights],
                self._dreams_dir / "insights.json",
            )
            atomic_json_save(
                [p.to_dict() for p in self.patterns],
                self._dreams_dir / "patterns.json",
            )
            atomic_json_save(
                [s.to_dict() for s in self.dream_log],
                self._dreams_dir / "dream_log.json",
            )
        except Exception as e:
            logger.error("Failed to save dream state: %s", e)

    def _record_session(self, session: DreamSession) -> None:
        """Record a dream session to the log."""
        self.dream_log.append(session)
        # Keep bounded
        if len(self.dream_log) > MAX_DREAM_LOG:
            self.dream_log = self.dream_log[-MAX_DREAM_LOG:]
