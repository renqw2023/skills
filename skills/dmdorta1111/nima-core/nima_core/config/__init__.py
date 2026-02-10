"""NIMA Core configuration module."""
from .nima_config import (
    NimaConfig,
    get_config,
    reload_config,
    refresh_paths,
    should_use_v2_for,
    enable_component,
    disable_all,
    NIMA_DATA_DIR,
    NIMA_MODELS_DIR,
    STORAGE_DIR,
    DATA_DIR,
)

# Standardized epsilon for zero-vector detection in cosine similarity
ZERO_NORM_THRESHOLD = 1e-8

__all__ = [
    "NimaConfig",
    "get_config",
    "reload_config",
    "should_use_v2_for",
    "enable_component",
    "disable_all",
    "refresh_paths",
    "NIMA_DATA_DIR",
    "NIMA_MODELS_DIR",
    "STORAGE_DIR",
    "DATA_DIR",
    "ZERO_NORM_THRESHOLD",
]
