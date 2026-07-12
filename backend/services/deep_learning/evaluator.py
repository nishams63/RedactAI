"""
Evaluator — Level 2 Deep Learning Enhancement
Generates performance audit comparisons (Accuracy, Latency, Memory, Throughput)
between traditional ML baseline models and Deep Learning models.
"""
import os
import json
import logging
from typing import Dict, Any

from services.deep_learning.utils import DL_MODELS_DIR
from services.ml.dataset_generator import ML_MODELS_DIR as ML_DIR

logger = logging.getLogger("redactai.dl.evaluator")


class DLEvaluator:
    """Evaluates and compares ML vs DL model performance."""

    @classmethod
    def get_comparison(cls) -> Dict[str, Any]:
        """
        Combines evaluation reports from Level 1 (ML) and Level 2 (DL)
        into a single unified comparison structure.
        """
        # Load ML evaluations
        ml_path = os.path.join(ML_DIR, "evaluation_results.json")
        ml_data = {}
        if os.path.exists(ml_path):
            try:
                with open(ml_path, "r") as f:
                    ml_data = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load ML evaluations: {e}")

        # Load DL evaluations
        dl_path = os.path.join(DL_MODELS_DIR, "training_report.json")
        dl_data = {}
        if os.path.exists(dl_path):
            try:
                with open(dl_path, "r") as f:
                    dl_data = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load DL evaluations: {e}")

        # Compile comparison metrics
        comparison = {
            "best_model_ml": ml_data.get("best_model", "Unknown"),
            "best_model_dl": dl_data.get("model_name", "nlpaueb/legal-bert-base-uncased"),
            "models": {}
        }

        # 1. Add ML Models
        for name, data in ml_data.get("models", {}).items():
            metrics = data.get("metrics", {})
            perf = data.get("performance", {})
            comparison["models"][name] = {
                "type": "ML (Traditional)",
                "accuracy": metrics.get("accuracy", 0.0),
                "precision": metrics.get("precision_macro", 0.0),
                "recall": metrics.get("recall_macro", 0.0),
                "f1": metrics.get("f1_macro", 0.0),
                "latency_ms": perf.get("inference_time_ms_per_sample", 0.0),
                # Traditional models have very high throughput
                "throughput": 1000.0 / max(perf.get("inference_time_ms_per_sample", 0.1), 0.001),
                "memory_mb": 15.0,  # Approximate size of scikit-learn models in RAM
                "training_time_seconds": perf.get("training_time_seconds", 0.0)
            }

        # 2. Add DL Model (LegalBERT)
        if dl_data:
            dl_metrics = dl_data.get("metrics", {})
            comparison["models"]["LegalBERT"] = {
                "type": "DL (Transformer)",
                "accuracy": dl_metrics.get("accuracy", 0.0),
                "precision": dl_metrics.get("precision_macro", 0.0),
                "recall": dl_metrics.get("recall_macro", 0.0),
                "f1": dl_metrics.get("f1_macro", 0.0),
                "latency_ms": dl_metrics.get("latency_ms", 0.0),
                "throughput": dl_metrics.get("throughput", 0.0),
                "memory_mb": dl_metrics.get("memory_mb", 0.0),
                "training_time_seconds": dl_data.get("training_time_seconds", 0.0)
            }

        return comparison
