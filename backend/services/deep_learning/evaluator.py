import os
import json
import logging
from typing import Dict, Any

from services.deep_learning.utils import DL_MODELS_DIR
from services.ml.dataset_generator import ML_MODELS_DIR as ML_DIR
from database.session import SessionLocal
from models.ai_models import AIModel

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
                "training_time_seconds": perf.get("training_time_seconds", 0.0),
                "model_size_mb": 5.0,
                "inference_time_ms": perf.get("inference_time_ms_per_sample", 0.0)
            }

        # 2. Add DL Model (LegalBERT)
        if dl_data:
            dl_metrics = dl_data.get("metrics", {})
            
            # Dynamically compute size
            artifacts_dir = os.path.dirname(DL_MODELS_DIR)
            transformer_path = os.path.join(artifacts_dir, "artifacts", "models", "transformer.pt")
            if os.path.exists(transformer_path):
                model_size = os.path.getsize(transformer_path) / (1024 * 1024)
            else:
                model_size = 418.0

            comparison["models"]["LegalBERT"] = {
                "type": "DL (Transformer)",
                "accuracy": dl_metrics.get("accuracy", 0.0),
                "precision": dl_metrics.get("precision_macro", 0.0) or dl_metrics.get("precision", 0.0),
                "recall": dl_metrics.get("recall_macro", 0.0) or dl_metrics.get("recall", 0.0),
                "f1": dl_metrics.get("f1_macro", 0.0),
                "latency_ms": dl_metrics.get("latency_ms", 0.0),
                "throughput": dl_metrics.get("throughput", 0.0),
                "memory_mb": dl_metrics.get("memory_mb", 0.0),
                "training_time_seconds": dl_data.get("training_time_seconds", 0.0),
                "model_size_mb": model_size,
                "inference_time_ms": dl_metrics.get("latency_ms", 0.0)
            }

        # 3. Add sequence models from DB registry
        db = SessionLocal()
        try:
            registered_models = db.query(AIModel).all()
            for model in registered_models:
                # Add DL models (e.g. LSTM, GRU, RNN, BiLSTM)
                model_name_lower = model.name.lower()
                if "classifier" in model_name_lower and "legalbert" not in model_name_lower:
                    params = model.parameters or {}
                    
                    # Compute file size dynamically
                    model_type_code = model_name_lower.split(" ")[0] # e.g. "lstm"
                    artifacts_dir = os.path.dirname(DL_MODELS_DIR)
                    model_path = os.path.join(artifacts_dir, "artifacts", "models", f"{model_type_code}.pt")
                    if os.path.exists(model_path):
                        model_size = os.path.getsize(model_path) / (1024 * 1024)
                    else:
                        model_size = 15.0

                    comparison["models"][model.name] = {
                        "type": f"DL ({model_type_code.upper()})",
                        "accuracy": params.get("accuracy", 0.0),
                        "precision": params.get("precision", 0.0),
                        "recall": params.get("recall", 0.0),
                        "f1": params.get("f1_macro", 0.0),
                        "latency_ms": params.get("latency_ms", 8.5),
                        "throughput": params.get("throughput", 120.0),
                        "memory_mb": params.get("memory_mb", 35.0),
                        "training_time_seconds": params.get("training_time", 0.0),
                        "model_size_mb": model_size,
                        "inference_time_ms": params.get("latency_ms", 8.5)
                    }
        except Exception as ex:
            logger.error(f"Failed to query registered models for comparison: {ex}")
        finally:
            db.close()

        return comparison
