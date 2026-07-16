import os
import yaml
from typing import Dict, Any, List
import pandas as pd

from utils.profiler import DeviceProfiler
from inference.predictor import PyTorchSequenceClassifier

class SequenceModelBenchmark:
    """
    Benchmarks lightweight recurrent PyTorch models (RNN, LSTM, GRU, BiLSTM).
    """
    def __init__(self, config_dir: str = "configs"):
        self.config_dir = config_dir
        with open(os.path.join(config_dir, "benchmark.yaml"), "r") as f:
            self.bench_cfg = yaml.safe_load(f)

    def run_benchmark(self, text_samples: List[str]) -> Dict[str, Any]:
        """Profiles accuracy, latency, and footprint across sequence architectures."""
        results = {}
        # Iterate over sequence models
        models_to_test = ["rnn", "lstm", "gru", "bilstm"]
        artifacts_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "artifacts")
        
        for m in models_to_test:
            model_path = os.path.join(artifacts_dir, "models", f"{m}.pt")
            
            # If model weights don't exist, we skip or profile initial state
            if not os.path.exists(model_path):
                results[m] = {
                    "status": "Unavailable",
                    "reason": f"Trained weights not found at {model_path}"
                }
                continue
                
            try:
                classifier = PyTorchSequenceClassifier(model_type=m, model_path=model_path, config_dir=self.config_dir)
                
                # Warmup
                dummy_feats = {}
                classifier.predict(dummy_feats, "warmup text")
                
                profiler = DeviceProfiler()
                profiler.start()
                
                runs = self.bench_cfg["sequence_benchmark"]["runs"]
                for _ in range(runs):
                    for sample in text_samples:
                        classifier.predict(dummy_feats, sample)
                        
                metrics = profiler.stop()
                
                # Get model size
                model_size_mb = os.path.getsize(model_path) / (1024 * 1024)
                
                results[m] = {
                    "status": "Available",
                    "type": "Sequence Model",
                    "model_size_mb": model_size_mb,
                    "latency_ms": metrics["latency_ms"] / (runs * len(text_samples)),
                    "memory_mb": metrics["memory_mb"],
                    "throughput": (runs * len(text_samples)) / (metrics["latency_ms"] / 1000.0)
                }
            except Exception as e:
                results[m] = {
                    "status": "Unavailable",
                    "reason": f"Execution failed: {e}"
                }
                
        return results
