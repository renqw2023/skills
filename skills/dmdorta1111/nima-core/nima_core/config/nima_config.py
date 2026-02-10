#!/usr/bin/env python3
"""
NIMA Feature Flags
==================
Control which NIMA components are active. All default to OFF for safety.

Enable via environment variables:
    NIMA_V2_AFFECTIVE=true
    NIMA_V2_BINDING=true
    NIMA_V2_FE=true
    NIMA_V2_ALL=true  # Enable everything

Author: NIMA Project
Date: 2026
"""

import os
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict


# Base paths - configurable via environment
# NOTE: These are evaluated at import time. If NIMA_DATA_DIR env var is set
# AFTER import (e.g. in NimaCore.__init__), call refresh_paths() to update.
NIMA_DATA_DIR = Path(os.getenv("NIMA_DATA_DIR", "./nima_data"))
NIMA_MODELS_DIR = Path(os.getenv("NIMA_MODELS_DIR", "./models"))
STORAGE_DIR = NIMA_DATA_DIR / "storage"
DATA_DIR = STORAGE_DIR / "data"


def refresh_paths():
    """Re-read path env vars. Call after setting NIMA_DATA_DIR/NIMA_MODELS_DIR at runtime."""
    global NIMA_DATA_DIR, NIMA_MODELS_DIR, STORAGE_DIR, DATA_DIR
    NIMA_DATA_DIR = Path(os.getenv("NIMA_DATA_DIR", "./nima_data"))
    NIMA_MODELS_DIR = Path(os.getenv("NIMA_MODELS_DIR", "./models"))
    STORAGE_DIR = NIMA_DATA_DIR / "storage"
    DATA_DIR = STORAGE_DIR / "data"


# Size limits to prevent unbounded growth
MAX_QUESTIONS = int(os.getenv("NIMA_MAX_QUESTIONS", "100"))
MAX_ACTIONS = int(os.getenv("NIMA_MAX_ACTIONS", "200"))
MAX_PREDICTIONS = int(os.getenv("NIMA_MAX_PREDICTIONS", "100"))
MAX_FE_HISTORY = int(os.getenv("NIMA_MAX_FE_HISTORY", "500"))
MAX_SEQUENCES = int(os.getenv("NIMA_MAX_SEQUENCES", "1000"))
MAX_CACHE_SIZE = int(os.getenv("NIMA_MAX_CACHE", "10000"))


@dataclass
class NimaConfig:
    """Feature flags for NIMA components."""
    
    # Layer 1: Affective Core (Panksepp's 7 affects)
    affective_core: bool = False
    
    # Layer 2: VSA Binding (FFT convolution)
    binding_layer: bool = False
    
    # Layer 3: Free Energy Consolidation
    consolidation_fe: bool = False
    
    # Layer 4: Episodic v2 (enhanced VSA)
    episodic_v2: bool = False
    
    # Layer 5: Semantic Hyperbolic
    semantic_hyperbolic: bool = False
    
    # Layer 6: Metacognitive (self-model)
    metacognitive: bool = False
    
    # Phase 2: Sparse Retrieval (10x speedup)
    sparse_retrieval: bool = True  # Default ON (validated)
    
    # Phase 1: Learned Projection (energy concentration)
    projection: bool = True  # Default ON (validated)
    
    # Global kill switch
    v2_enabled: bool = True
    
    def any_enabled(self) -> bool:
        """Check if any v2 feature is enabled."""
        if not self.v2_enabled:
            return False
        return any([
            self.affective_core,
            self.binding_layer,
            self.consolidation_fe,
            self.episodic_v2,
            self.semantic_hyperbolic,
            self.metacognitive,
            self.sparse_retrieval,
            self.projection,
        ])
    
    def to_dict(self) -> Dict[str, bool]:
        """Export as dictionary."""
        return {
            "v2_enabled": self.v2_enabled,
            "affective_core": self.affective_core,
            "binding_layer": self.binding_layer,
            "consolidation_fe": self.consolidation_fe,
            "episodic_v2": self.episodic_v2,
            "semantic_hyperbolic": self.semantic_hyperbolic,
            "metacognitive": self.metacognitive,
            "sparse_retrieval": self.sparse_retrieval,
            "projection": self.projection,
        }
    
    @classmethod
    def from_env(cls) -> "NimaConfig":
        """Load config from environment variables."""
        def env_bool(key: str, default: bool = False) -> bool:
            val = os.environ.get(key, "").lower()
            if val in ("true", "1", "yes", "on"):
                return True
            if val in ("false", "0", "no", "off"):
                return False
            return default
        
        # Check for global enable
        all_enabled = env_bool("NIMA_V2_ALL", True)
        
        # Sparse retrieval and projection default ON (validated)
        sparse_default = True
        projection_default = True
        
        return cls(
            affective_core=all_enabled or env_bool("NIMA_V2_AFFECTIVE"),
            binding_layer=all_enabled or env_bool("NIMA_V2_BINDING"),
            consolidation_fe=all_enabled or env_bool("NIMA_V2_FE"),
            episodic_v2=all_enabled or env_bool("NIMA_V2_EPISODIC"),
            semantic_hyperbolic=all_enabled or env_bool("NIMA_V2_SEMANTIC"),
            metacognitive=all_enabled or env_bool("NIMA_V2_META"),
            sparse_retrieval=env_bool("NIMA_SPARSE_RETRIEVAL", sparse_default),
            projection=env_bool("NIMA_PROJECTION", projection_default),
            v2_enabled=not env_bool("NIMA_V2_DISABLED"),
        )


# Singleton config instance with thread safety
_config: NimaConfig = None
_config_lock = threading.Lock()


def get_config() -> NimaConfig:
    """Get the global config (loads from env on first call). Thread-safe."""
    global _config
    if _config is None:
        with _config_lock:
            if _config is None:  # Double-checked locking
                _config = NimaConfig.from_env()
    return _config


def reload_config() -> NimaConfig:
    """Force reload config from environment. Thread-safe."""
    global _config
    with _config_lock:
        _config = NimaConfig.from_env()
    return _config


def should_use_v2_for(component: str) -> bool:
    """Check if v2 should be used for a specific component."""
    cfg = get_config()
    
    if not cfg.v2_enabled:
        return False
    
    mapping = {
        "affect": cfg.affective_core,
        "affect_processing": cfg.affective_core,
        "affective": cfg.affective_core,
        "binding": cfg.binding_layer,
        "consolidation": cfg.consolidation_fe,
        "free_energy": cfg.consolidation_fe,
        "episodic": cfg.episodic_v2,
        "semantic": cfg.semantic_hyperbolic,
        "meta": cfg.metacognitive,
        "metacognitive": cfg.metacognitive,
        "sparse": cfg.sparse_retrieval,
        "sparse_retrieval": cfg.sparse_retrieval,
        "retrieval": cfg.sparse_retrieval,
        "projection": cfg.projection,
        "project": cfg.projection,
    }
    
    return mapping.get(component.lower(), False)


def enable_component(component: str) -> bool:
    """Programmatically enable a component (for testing). Thread-safe."""
    with _config_lock:  # Thread safety
        cfg = get_config()
        
        mapping = {
            "affective": "affective_core",
            "binding": "binding_layer",
            "consolidation": "consolidation_fe",
            "fe": "consolidation_fe",
            "episodic": "episodic_v2",
            "semantic": "semantic_hyperbolic",
            "meta": "metacognitive",
            "sparse": "sparse_retrieval",
            "retrieval": "sparse_retrieval",
            "projection": "projection",
        }
        
        attr = mapping.get(component.lower())
        if attr and hasattr(cfg, attr):
            setattr(cfg, attr, True)
            return True
        return False


def disable_all() -> None:
    """Disable all v2 components (emergency rollback). Thread-safe."""
    with _config_lock:  # Thread safety
        cfg = get_config()
        cfg.affective_core = False
        cfg.binding_layer = False
        cfg.consolidation_fe = False
        cfg.episodic_v2 = False
        cfg.semantic_hyperbolic = False
        cfg.metacognitive = False
        cfg.sparse_retrieval = False
        cfg.projection = False


# CLI for testing
if __name__ == "__main__":
    import json
    cfg = get_config()
    print("NIMA Configuration:")
    print(json.dumps(cfg.to_dict(), indent=2))
    print(f"\nAny enabled: {cfg.any_enabled()}")
