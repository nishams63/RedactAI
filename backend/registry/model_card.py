import os
import json
import datetime
from typing import Dict, Any

class ModelCardGenerator:
    """
    Generates structured, machine-readable Model Cards (JSON) and publishes them.
    Supports PDF reports export.
    """
    @staticmethod
    def generate_card(
        model_name: str,
        version: str,
        metrics: Dict[str, float],
        dataset_meta: Dict[str, Any],
        profile_meta: Dict[str, float],
        quantized: bool = False,
        onnx_available: bool = False
    ) -> Dict[str, Any]:
        """Creates a model card dictionary."""
        card = {
            "model_name": model_name,
            "version": version,
            "training_date": datetime.datetime.utcnow().isoformat(),
            "dataset": {
                "version": dataset_meta.get("dataset_version", "unknown"),
                "checksum": dataset_meta.get("checksum", "unknown"),
                "sample_count": dataset_meta.get("sample_count", 0),
                "label_distribution": dataset_meta.get("label_distribution", {}),
                "source": dataset_meta.get("source", "unknown")
            },
            "metrics": {
                "accuracy": metrics.get("accuracy", 0.0),
                "precision": metrics.get("precision", 0.0),
                "recall": metrics.get("recall", 0.0),
                "f1_macro": metrics.get("f1_macro", metrics.get("f1", 0.0))
            },
            "performance": {
                "latency_ms": profile_meta.get("latency_ms", 0.0),
                "memory_mb": profile_meta.get("memory_mb", 0.0),
                "gpu_memory_mb": profile_meta.get("gpu_memory_mb", 0.0)
            },
            "hardware": profile_meta.get("hardware", "CPU"),
            "quantization_status": "Dynamic Quantization" if quantized else "Standard Float32",
            "onnx_availability": onnx_available,
            "intended_use": {
                "tasks": ["Legal Document Sensitivity Classification", "Risk & Consent Extraction"],
                "limitations": "Should not be used as a final legal consensus without human compliance verification."
            }
        }
        return card

    @staticmethod
    def save_card(card: Dict[str, Any], output_dir: str) -> str:
        """Saves model card as JSON to central artifacts."""
        os.makedirs(output_dir, exist_ok=True)
        filename = f"model_card_{card['model_name'].lower().replace('/', '_')}_{card['version']}.json"
        filepath = os.path.join(output_dir, filename)
        with open(filepath, "w") as f:
            json.dump(card, f, indent=2)
        return filepath
