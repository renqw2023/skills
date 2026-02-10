#!/usr/bin/env python3
"""
NIMA Heartbeat Service
======================
Generic background memory capture service.

Consumers provide a message_source function that returns new messages.
The service periodically calls it and processes through the NIMA pipeline.

Usage:
    from nima_core.services.heartbeat import NimaHeartbeat
    
    def my_source():
        return [{"who": "user", "what": "hello", "importance": 0.5}]
    
    heartbeat = NimaHeartbeat(nima, message_source=my_source, interval_minutes=10)
    heartbeat.start()  # Blocking
    # or
    heartbeat.start_background()  # Non-blocking thread

Author: NIMA Project
"""

import os
import time
import signal
import logging
import threading
from datetime import datetime, timedelta
from typing import Callable, Dict, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


# Default emotion words that trigger force-consolidation
DEFAULT_EMOTION_WORDS = {
    'love', 'proud', 'excited', 'happy', 'grateful', 'amazing',
    'scared', 'worried', 'angry', 'frustrated', 'sad', 'hurt',
    'beautiful', 'miss', 'hope', 'trust', 'faith',
}

# Default importance markers that trigger force-consolidation
DEFAULT_IMPORTANCE_MARKERS = {
    'remember', 'important', 'never forget', 'milestone',
    'decision', 'promise', 'birthday', 'anniversary',
    'family', 'children',
}

# Default noise patterns to skip
DEFAULT_NOISE_PATTERNS = [
    'heartbeat_ok', 'system exec', 'command completed',
    'process exited', 'no output', 'test data',
]


class SmartConsolidation:
    """
    Configurable smart consolidation for memory importance scoring.
    
    Bots configure their own important people, emotion words, and
    importance markers. No hardcoded names — everything is customizable.
    
    Usage:
        smart = SmartConsolidation(
            important_people={"alice": 1.5, "bob": 1.3},
            emotion_words={"love", "excited", "proud"},
            importance_markers={"family", "milestone"},
        )
        result = smart.score(who="alice", what="I'm so proud of you!")
        # result = {"importance": 0.9, "force": True, "reasons": ["emotion", "important_person"]}
    """
    
    def __init__(
        self,
        important_people: Optional[Dict[str, float]] = None,
        emotion_words: Optional[set] = None,
        importance_markers: Optional[set] = None,
        noise_patterns: Optional[List[str]] = None,
        bot_name: str = "assistant",
        default_weight: float = 0.7,
        bot_weight: float = 1.0,
        user_weight: float = 0.8,
        force_threshold: float = 0.8,
    ):
        """
        Args:
            important_people: Dict mapping lowercase names to weight multipliers
                              e.g. {"alice": 1.5, "bob": 1.3}
            emotion_words: Set of words that trigger emotional consolidation
            importance_markers: Set of words/phrases that mark important content
            noise_patterns: List of patterns to skip (noise filtering)
            bot_name: The bot's own name (for source weighting)
            default_weight: Weight for unknown sources
            bot_weight: Weight for the bot's own messages
            user_weight: Weight for generic "user" messages
            force_threshold: Importance threshold for force-consolidation
        """
        self.important_people = {k.lower(): v for k, v in (important_people or {}).items()}
        self.emotion_words = emotion_words or DEFAULT_EMOTION_WORDS
        self.importance_markers = importance_markers or DEFAULT_IMPORTANCE_MARKERS
        self.noise_patterns = [p.lower() for p in (noise_patterns or DEFAULT_NOISE_PATTERNS)]
        self.bot_name = bot_name.lower()
        self.default_weight = default_weight
        self.bot_weight = bot_weight
        self.user_weight = user_weight
        self.force_threshold = force_threshold
        
        # Stats
        self.stats = {
            "scored": 0,
            "forced": 0,
            "skipped_noise": 0,
            "emotion_boosts": 0,
            "importance_boosts": 0,
        }
    
    def is_noise(self, text: str) -> bool:
        """Check if text matches noise patterns."""
        text_lower = text.lower()
        return any(p in text_lower for p in self.noise_patterns)
    
    def score(self, who: str, what: str, base_importance: float = 0.5) -> Dict:
        """
        Score a memory for consolidation importance.
        
        Args:
            who: Who said/did it
            what: Content text
            base_importance: Starting importance [0-1]
        
        Returns:
            Dict with importance, force flag, and reasons
        """
        self.stats["scored"] += 1
        reasons = []
        what_lower = what.lower()
        who_lower = who.lower()
        
        # Noise check
        if self.is_noise(what_lower):
            self.stats["skipped_noise"] += 1
            return {"importance": 0.0, "force": False, "reasons": ["noise"], "skip": True}
        
        # Source weighting
        if who_lower in self.important_people:
            source_weight = self.important_people[who_lower]
            reasons.append("important_person")
        elif who_lower == "user":
            source_weight = self.user_weight
        elif who_lower == self.bot_name or who_lower == "assistant":
            source_weight = self.bot_weight
        else:
            source_weight = self.default_weight
        
        smart_importance = base_importance * source_weight
        
        # Emotion detection
        has_emotion = any(w in what_lower for w in self.emotion_words)
        if has_emotion:
            smart_importance = max(smart_importance, 0.8)
            reasons.append("emotion")
            self.stats["emotion_boosts"] += 1
        
        # Importance markers
        is_important = any(m in what_lower for m in self.importance_markers)
        if is_important:
            smart_importance = max(smart_importance, 0.85)
            reasons.append("important_marker")
            self.stats["importance_boosts"] += 1
        
        # Cap at 1.0
        smart_importance = min(1.0, smart_importance)
        
        # Force consolidation?
        force = smart_importance >= self.force_threshold
        if force:
            self.stats["forced"] += 1
        
        return {
            "importance": smart_importance,
            "force": force,
            "reasons": reasons,
            "skip": False,
        }


class NimaHeartbeat:
    """Generic heartbeat service for periodic memory capture."""
    
    def __init__(
        self,
        nima,  # NimaCore instance
        message_source: Optional[Callable[[], List[Dict]]] = None,
        interval_minutes: int = 10,
        consolidation_hour: int = 2,  # 2 AM
        smart_consolidation: Optional[SmartConsolidation] = None,
        markdown_dir: Optional[str] = None,
        markdown_export_path: Optional[str] = None,
        extra_markdown_files: Optional[List[str]] = None,
    ):
        """
        Args:
            nima: NimaCore instance
            message_source: Callable returning list of message dicts
            interval_minutes: Capture interval
            consolidation_hour: Hour for dream consolidation (0-23)
            smart_consolidation: SmartConsolidation instance for importance scoring
                                 If None, creates default (no important people configured)
            markdown_dir: Directory with markdown memory files for bidirectional sync
            markdown_export_path: Where to export NIMA memories as markdown
            extra_markdown_files: Additional files to ingest (e.g. MEMORY.md)
        """
        self.nima = nima
        self.message_source = message_source
        self.interval = timedelta(minutes=interval_minutes)
        self.consolidation_hour = consolidation_hour
        self.smart = smart_consolidation or SmartConsolidation()
        self._shutdown = False
        self._thread = None
        
        # Markdown bridge config
        self.markdown_dir = markdown_dir
        self.markdown_export_path = markdown_export_path
        self.extra_markdown_files = extra_markdown_files
        self.last_capture = None
        self.last_consolidation = None
        self.stats = {"captures": 0, "memories_added": 0, "smart_skipped": 0}
        
        # Heartbeat hygiene — keeps HEARTBEAT.md lean
        self._hygiene = None
        try:
            from .heartbeat_hygiene import HeartbeatHygiene
            workspace = os.environ.get("OPENCLAW_WORKSPACE")
            if workspace:
                self._hygiene = HeartbeatHygiene(workspace=workspace)
                logger.debug("Heartbeat hygiene enabled")
        except Exception as e:
            logger.debug(f"Heartbeat hygiene not available: {e}")
    
    def capture_once(self) -> Dict:
        """Run a single capture cycle with smart consolidation."""
        if not self.message_source:
            return {"status": "no_source"}
        
        messages = self.message_source()
        added = 0
        skipped = 0
        forced = 0
        now = datetime.now()
        
        for msg in messages:
            # Add temporal triple format if not present
            if "timestamp_ms" not in msg:
                msg["timestamp_ms"] = int(now.timestamp() * 1000)
            if "timestamp_iso" not in msg:
                msg["timestamp_iso"] = now.isoformat()
            if "when" not in msg:
                msg["when"] = now.strftime("%Y-%m-%d %H:%M")
            
            who = msg.get("who", "user")
            what = msg.get("what", "")
            base_importance = msg.get("importance", 0.5)
            
            # Smart consolidation scoring
            score_result = self.smart.score(who, what, base_importance)
            
            # Skip noise
            if score_result.get("skip"):
                skipped += 1
                self.stats["smart_skipped"] += 1
                logger.debug(f"Skipped noise: {who}: {what[:50]}")
                continue
            
            # Apply smart importance
            smart_importance = score_result["importance"]
            
            result = self.nima.experience(
                content=what,
                who=who,
                importance=smart_importance,
                timestamp_ms=msg.get("timestamp_ms"),
                timestamp_iso=msg.get("timestamp_iso"),
                when=msg.get("when"),
            )
            
            # Force consolidation override
            if score_result["force"] and not result.get("stored"):
                # FE said skip, but smart says force — capture explicitly
                self.nima.capture(who=who, what=what, importance=smart_importance)
                result["stored"] = True
                forced += 1
                logger.info(f"Smart override: {who}: {what[:50]} (reasons: {score_result['reasons']})")
            
            if result.get("stored"):
                added += 1
        
        self.last_capture = datetime.now()
        self.stats["captures"] += 1
        self.stats["memories_added"] += added
        
        # Export NIMA → markdown after capture (if configured)
        if added > 0 and self.markdown_export_path:
            try:
                from .markdown_bridge import MarkdownBridge
                bridge = MarkdownBridge(self.nima, agent_name=self.nima.name)
                bridge.export_to_markdown(self.markdown_export_path)
            except Exception as e:
                logger.debug(f"Markdown export skipped: {e}")
        
        logger.info(f"Heartbeat: {added}/{len(messages)} stored, {skipped} noise, {forced} forced")
        return {"added": added, "total": len(messages), "skipped": skipped, "forced": forced}
    
    def start(self):
        """Start heartbeat loop (blocking)."""
        logger.info(f"NIMA Heartbeat starting (interval={self.interval})")
        
        signal.signal(signal.SIGTERM, lambda s, f: setattr(self, '_shutdown', True))
        signal.signal(signal.SIGINT, lambda s, f: setattr(self, '_shutdown', True))
        
        # Run hygiene check on startup
        self._run_hygiene()
        
        # Initial capture
        self.capture_once()
        
        while not self._shutdown:
            now = datetime.now()
            
            # Check consolidation time
            if (now.hour == self.consolidation_hour and 
                now.minute < 10 and
                (self.last_consolidation is None or 
                 self.last_consolidation.date() != now.date())):
                
                # Ingest markdown → NIMA before consolidation
                if self.markdown_dir:
                    try:
                        from .markdown_bridge import MarkdownBridge
                        bridge = MarkdownBridge(self.nima, agent_name=self.nima.name)
                        result = bridge.sync(
                            markdown_dir=self.markdown_dir,
                            export_path=self.markdown_export_path or str(
                                Path(self.markdown_dir) / "nima_export.md"
                            ),
                            extra_files=self.extra_markdown_files,
                        )
                        logger.info(f"Markdown sync: {result['ingest']['added']} ingested, "
                                   f"{result['export']['memories_exported']} exported")
                    except Exception as e:
                        logger.warning(f"Markdown sync failed: {e}")
                
                logger.info("Running dream consolidation...")
                self.nima.dream()
                self.last_consolidation = now
            
            # Check capture interval
            if self.last_capture is None or (now - self.last_capture) >= self.interval:
                self._run_hygiene()
                self.capture_once()
            
            time.sleep(60)
        
        logger.info("Heartbeat stopped")
    
    def start_background(self) -> threading.Thread:
        """Start heartbeat in background thread."""
        self._thread = threading.Thread(target=self.start, daemon=True)
        self._thread.start()
        return self._thread
    
    def _run_hygiene(self):
        """Run HEARTBEAT.md hygiene check — archive bloat before it accumulates."""
        if not self._hygiene:
            return
        try:
            result = self._hygiene.run()
            if result.get("archived"):
                logger.info(result["message"])
            else:
                logger.debug(result["message"])
        except Exception as e:
            logger.debug(f"Hygiene check failed: {e}")
    
    def stop(self):
        """Stop the heartbeat."""
        self._shutdown = True
