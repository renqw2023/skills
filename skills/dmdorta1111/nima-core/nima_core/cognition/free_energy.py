#!/usr/bin/env python3
"""
Free Energy Consolidation - NIMA Tier 2
=========================================

Replaces heuristic "surprise threshold" with principled Free Energy calculation.

Based on Friston's Free Energy Principle:
    F = Prediction Error + Complexity Cost

Key insight: Use extracted SCHEMAS as our generative model.
- Good schema match = low prediction error = DON'T consolidate (already known)
- Poor schema match + low complexity = HIGH free energy = CONSOLIDATE (novel)
- Poor schema match + high complexity = noise = DON'T consolidate

Author: NIMA Project
Date: 2026
"""

import numpy as np
import torch
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple
from collections import deque
from datetime import datetime
import json
import threading
import logging
import os

logger = logging.getLogger(__name__)

# Paths use environment or default
from ..config import NIMA_DATA_DIR

SCHEMAS_DIR = NIMA_DATA_DIR / "schemas"
FE_STATE_FILE = NIMA_DATA_DIR / "free_energy_state.json"


class ConsolidationReason(Enum):
    """Reasons for consolidation decision."""
    HIGH_FREE_ENERGY = "high_free_energy"
    HIGH_EPISTEMIC_VALUE = "high_epistemic_value"
    EMOTIONAL_SALIENCE = "emotional_salience"
    NOVEL_PATTERN = "novel_pattern"
    BELOW_THRESHOLD = "below_threshold"


@dataclass
class FreeEnergyResult:
    """Result of free energy calculation."""
    should_consolidate: bool
    priority: float
    reason: ConsolidationReason
    free_energy: float
    prediction_error: float
    complexity: float
    epistemic_value: float
    precision: float
    best_schema_match: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            'should_consolidate': self.should_consolidate,
            'priority': float(self.priority),
            'reason': self.reason.value,
            'free_energy': float(self.free_energy),
            'prediction_error': float(self.prediction_error),
            'complexity': float(self.complexity),
            'epistemic_value': float(self.epistemic_value),
            'precision': float(self.precision),
            'best_schema_match': self.best_schema_match,
        }


class SchemaBasedModel:
    """
    Generative model based on extracted schemas.
    
    Schemas are "what I expect to see" — learned abstractions.
    New experiences are compared against schemas to compute prediction error.
    """
    
    def __init__(self, schemas_dir: Path = SCHEMAS_DIR, dimension: int = 50000):
        self.schemas_dir = schemas_dir
        self.dimension = dimension
        self.schemas: Dict[str, torch.Tensor] = {}
        self.schema_metadata: Dict[str, Dict] = {}
        self._load_schemas()
        
        # Prior: uniform distribution (maximum entropy)
        self.prior_mean = torch.zeros(dimension)
        self.prior_var = 1.0
    
    def _load_schemas(self):
        """Load all persisted schemas."""
        if not self.schemas_dir.exists():
            logger.warning("No schemas directory found")
            return
        
        for schema_file in self.schemas_dir.glob("*.pt"):
            try:
                from ..utils import safe_torch_load
                data = safe_torch_load(schema_file)
                
                # Handle both old format (raw tensor) and new format (dict)
                if isinstance(data, dict):
                    # New format: dict with metadata
                    theme = data.get('theme', schema_file.stem)
                    vector = data['vector']
                    metadata = {
                        'strength': data.get('strength', 0.5),
                        'distinctness': data.get('distinctness', 0.5),
                        'created_at': data.get('created_at', ''),
                    }
                else:
                    # Old format: raw tensor - try to load metadata from JSON
                    theme = schema_file.stem
                    vector = data
                    
                    # Try to load metadata from corresponding JSON file
                    json_path = schema_file.with_suffix('.json')
                    if json_path.exists():
                        import json
                        with open(json_path, 'r') as f:
                            json_data = json.load(f)
                        metadata = {
                            'strength': json_data.get('strength', 0.5),
                            'distinctness': json_data.get('distinctness', 0.5),
                            'created_at': json_data.get('created_at', ''),
                        }
                    else:
                        metadata = {
                            'strength': 0.5,
                            'distinctness': 0.5,
                            'created_at': '',
                        }
                
                self.schemas[theme] = vector
                self.schema_metadata[theme] = metadata
                
            except Exception as e:
                logger.warning(f"Could not load schema {schema_file}: {e}")
        
        logger.info(f"Loaded {len(self.schemas)} schemas for FE calculation")
    
    def predict(self, observation: torch.Tensor) -> Tuple[torch.Tensor, str]:
        """Predict observation using best-matching schema."""
        if not self.schemas:
            return self.prior_mean, "prior"
        
        best_schema = None
        best_sim = -float('inf')
        
        obs_flat = observation.flatten().float()
        
        for name, schema_vec in self.schemas.items():
            schema_flat = schema_vec.flatten().float()
            
            sim = torch.dot(obs_flat, schema_flat) / (
                torch.norm(obs_flat) * torch.norm(schema_flat) + 1e-8
            )
            
            if sim > best_sim:
                best_sim = sim
                best_schema = name
        
        schema_weight = max(0, float(best_sim))
        prediction = schema_weight * self.schemas[best_schema] + (1 - schema_weight) * self.prior_mean
        
        return prediction, best_schema
    
    def entropy(self) -> float:
        """Entropy of the generative model (uncertainty)."""
        if not self.schemas:
            return 10.0
        
        avg_strength = np.mean([m['strength'] for m in self.schema_metadata.values()])
        entropy = 10.0 / (1 + len(self.schemas) * avg_strength)
        
        return entropy
    
    def update(self, observation: torch.Tensor, commit: bool = False) -> float:
        """Update model with new observation."""
        return self.entropy() * 0.99


class FreeEnergyConsolidation:
    """
    Free Energy-based memory consolidation.
    
    Core equation:
        F = Prediction Error + Complexity
    """
    
    def __init__(self, embedder=None, schemas_dir: Path = None):
        """
        Initialize FE consolidation.
        
        Args:
            embedder: EmbeddingCache with projection (optional)
            schemas_dir: Directory containing schema files
        """
        self.embedder = embedder
        if schemas_dir is None:
            schemas_dir = SCHEMAS_DIR
        self._lock = threading.RLock()
        self.model = SchemaBasedModel(schemas_dir=schemas_dir)
        
        # Adaptive baseline
        self.baseline_fe = 0.5
        self.precision = 1.0
        
        self.fe_history: deque = deque(maxlen=250)
        self.epistemic_history: deque = deque(maxlen=250)
        
        self.baseline_adaptation_rate = 0.05
        self.min_fe_threshold = 0.55
        self.min_epistemic_threshold = 0.01
        
        self._load_state()
        
        if self.embedder is None:
            self._load_embedder()
    
    def _load_embedder(self):
        """Load embedder with projection."""
        try:
            from ..embeddings import EmbeddingCache
            self.embedder = EmbeddingCache(enable_projection=True)
            logger.info("Embedder loaded for FE calculation")
        except Exception as e:
            logger.warning(f"Could not load embedder: {e}")
            self.embedder = None
    
    def _load_state(self):
        """Load persisted state."""
        with self._lock:
            if FE_STATE_FILE.exists():
                try:
                    with open(FE_STATE_FILE, 'r') as f:
                        state = json.load(f)
                    self.baseline_fe = state.get('baseline_fe', 1.0)
                    self.fe_history = deque(state.get('fe_history', [])[-100:], maxlen=250)
                    self.epistemic_history = deque(state.get('epistemic_history', [])[-100:], maxlen=250)
                except Exception as e:
                    logger.warning(f"Could not load FE state: {e}")
    
    def _save_state(self):
        """Save state."""
        with self._lock:
            try:
                from ..utils import atomic_json_save
                state = {
                    'baseline_fe': self.baseline_fe,
                    'fe_history': list(self.fe_history)[-100:],
                    'epistemic_history': list(self.epistemic_history)[-100:],
                    'updated_at': datetime.now().isoformat(),
                }
                atomic_json_save(state, FE_STATE_FILE)
            except Exception as e:
                logger.warning(f"Could not save FE state: {e}")
    
    def compute_free_energy(self, observation: torch.Tensor) -> Tuple[float, float, float, str]:
        """
        Compute variational free energy.
        
        F = Prediction Error + Complexity
        """
        obs = observation.flatten().float()
        obs_norm = torch.norm(obs)
        
        if obs_norm < 1e-8:
            return 1.0, 1.0, 0.0, "prior"
        
        best_schema = "prior"
        best_sim = -1.0
        all_sims = []
        
        for name, schema_vec in self.model.schemas.items():
            schema = schema_vec.flatten().float()
            schema_norm = torch.norm(schema)
            
            if schema_norm < 1e-8:
                continue
            
            sim = float(torch.dot(obs, schema) / (obs_norm * schema_norm))
            all_sims.append(sim)
            
            if sim > best_sim:
                best_sim = sim
                best_schema = name
        
        prediction_error = (1.0 - best_sim) / 2.0
        
        if all_sims:
            avg_sim = np.mean(all_sims)
            complexity = (1.0 - avg_sim) / 2.0
        else:
            complexity = 1.0
        
        free_energy = prediction_error + 0.3 * complexity
        
        return free_energy, prediction_error, complexity, best_schema
    
    def compute_epistemic_value(self, observation: torch.Tensor) -> float:
        """Expected information gain from encoding this experience."""
        H_before = self.model.entropy()
        H_after = self.model.update(observation, commit=False)
        info_gain = max(0, H_before - H_after)
        return info_gain
    
    def should_consolidate(self, text: str, affect: Optional[Dict] = None) -> FreeEnergyResult:
        """
        Principled consolidation decision using Free Energy.
        
        Args:
            text: Experience text to evaluate
            affect: Optional affect dict with 'valence' and 'arousal'
        """
        affect = affect or {'valence': 0.0, 'arousal': 0.5}
        
        if self.embedder is None:
            return FreeEnergyResult(
                should_consolidate=True,
                priority=0.5,
                reason=ConsolidationReason.BELOW_THRESHOLD,
                free_energy=0.0,
                prediction_error=0.0,
                complexity=0.0,
                epistemic_value=0.0,
                precision=1.0,
            )
        
        embedding = self.embedder.encode_single(text)
        if embedding is None:
            return FreeEnergyResult(
                should_consolidate=True,
                priority=0.5,
                reason=ConsolidationReason.BELOW_THRESHOLD,
                free_energy=0.0,
                prediction_error=0.0,
                complexity=0.0,
                epistemic_value=0.0,
                precision=1.0,
            )
        
        obs = torch.from_numpy(embedding) if isinstance(embedding, np.ndarray) else embedding
        
        fe, pred_error, complexity, best_schema = self.compute_free_energy(obs)
        epistemic = self.compute_epistemic_value(obs)
        
        arousal = affect.get('arousal', 0.5)
        valence = affect.get('valence', 0.0)
        precision = 1.0 + arousal * abs(valence)
        
        weighted_fe = fe * precision
        
        result = FreeEnergyResult(
            should_consolidate=False,
            priority=0.0,
            reason=ConsolidationReason.BELOW_THRESHOLD,
            free_energy=fe,
            prediction_error=pred_error,
            complexity=complexity,
            epistemic_value=epistemic,
            precision=precision,
            best_schema_match=best_schema,
        )
        
        adaptive_threshold = max(self.baseline_fe, self.min_fe_threshold)
        if weighted_fe > adaptive_threshold:
            result.should_consolidate = True
            result.priority = weighted_fe
            result.reason = ConsolidationReason.HIGH_FREE_ENERGY
        elif epistemic > max(self.min_epistemic_threshold, 0.05):
            result.should_consolidate = True
            result.priority = epistemic
            result.reason = ConsolidationReason.HIGH_EPISTEMIC_VALUE
        elif abs(valence) > 0.7 or arousal > 0.8:
            result.should_consolidate = True
            result.priority = arousal * abs(valence)
            result.reason = ConsolidationReason.EMOTIONAL_SALIENCE
        elif best_schema == "prior" and complexity < 0.5:
            result.should_consolidate = True
            result.priority = 1.0 - complexity
            result.reason = ConsolidationReason.NOVEL_PATTERN
        
        with self._lock:
            self.fe_history.append(fe)
            self.epistemic_history.append(epistemic)
            
            if len(self.fe_history) >= 10:
                recent_avg = np.mean(self.fe_history[-10:])
                self.baseline_fe = (
                    (1 - self.baseline_adaptation_rate) * self.baseline_fe +
                    self.baseline_adaptation_rate * recent_avg
                )
            
            if len(self.fe_history) % 50 == 0:
                self._save_state()
        
        return result
    
    def batch_evaluate(self, texts: List[str]) -> List[FreeEnergyResult]:
        """Evaluate multiple texts."""
        return [self.should_consolidate(text) for text in texts]
    
    def get_stats(self) -> Dict:
        """Get FE system statistics."""
        return {
            'baseline_fe': self.baseline_fe,
            'fe_history_len': len(self.fe_history),
            'avg_fe': np.mean(self.fe_history) if self.fe_history else 0,
            'avg_epistemic': np.mean(self.epistemic_history) if self.epistemic_history else 0,
            'schemas_loaded': len(self.model.schemas),
            'model_entropy': self.model.entropy(),
        }


def main():
    """Test FE consolidation."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Free Energy Consolidation")
    parser.add_argument("action", choices=["test", "stats", "evaluate"],
                        help="Action to perform")
    parser.add_argument("--text", "-t", help="Text to evaluate")
    parser.add_argument("--json", action="store_true")
    
    args = parser.parse_args()
    
    fe = FreeEnergyConsolidation()
    
    if args.action == "test":
        test_texts = [
            "The user said they're excited about the NIMA project.",
            "The weather is nice today.",
            "I discovered a profound connection between consciousness and memory.",
            "Testing 123.",
        ]
        
        logger.info("Free Energy Consolidation Test")
        logger.info(f"Schemas loaded: {len(fe.model.schemas)}")
        logger.info(f"Model entropy: {fe.model.entropy():.3f}")
        
        for text in test_texts:
            result = fe.should_consolidate(text)
            logger.debug(f"Text: \"{text[:50]}...\"")
            logger.debug(f"  Consolidate: {result.should_consolidate}")
            logger.debug(f"  Reason: {result.reason.value}")
            logger.debug(f"  FE={result.free_energy:.3f}, PE={result.prediction_error:.3f}")
            logger.debug(f"  Best schema: {result.best_schema_match}")
    
    elif args.action == "stats":
        stats = fe.get_stats()
        if args.json:
            print(json.dumps(stats, indent=2))
        else:
            logger.info("Free Energy Statistics:")
            for k, v in stats.items():
                logger.info(f"   {k}: {v}")
    
    elif args.action == "evaluate":
        if not args.text:
            logger.error("--text required for evaluate")
            return
        
        result = fe.should_consolidate(args.text)
        if args.json:
            print(json.dumps(result.to_dict(), indent=2))
        else:
            logger.info(f"Text: \"{args.text[:80]}\"")
            logger.info(f"Should consolidate: {result.should_consolidate}")
            logger.info(f"  Reason: {result.reason.value}")
            logger.info(f"  Priority: {result.priority:.3f}")
            logger.debug(f"Metrics:")
            logger.debug(f"  Free Energy: {result.free_energy:.4f}")
            logger.debug(f"  Prediction Error: {result.prediction_error:.4f}")
            logger.debug(f"  Complexity: {result.complexity:.4f}")
            logger.debug(f"  Epistemic Value: {result.epistemic_value:.4f}")
            logger.debug(f"  Precision: {result.precision:.4f}")
            logger.debug(f"  Best Schema: {result.best_schema_match}")


if __name__ == "__main__":
    main()
