import os
import yaml
from typing import Dict, Any, List
from utils.profiler import DeviceProfiler

class TransformerModelBenchmark:
    """
    Benchmarks fine-tuned LegalBERT models under PyTorch and ONNX serving.
    """
    def __init__(self, config_dir: str = "configs"):
        self.config_dir = config_dir
        with open(os.path.join(config_dir, "benchmark.yaml"), "r") as f:
            self.bench_cfg = yaml.safe_load(f)

    def run_benchmark(self, text_samples: List[str]) -> Dict[str, Any]:
        """Profiles accuracy, latency, and footprint of LegalBERT under PyTorch & ONNX."""
        results = {}
        artifacts_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "artifacts")
        
        # 1. PyTorch benchmark
        pt_path = os.path.join(artifacts_dir, "models", "transformer.pt")
        if not os.path.exists(pt_path):
            # Check legacy folder fallback
            pt_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dl_models", "best_model.pt")
            
        if os.path.exists(pt_path):
            try:
                from services.deep_learning.predictor import LegalBERTClassifier
                classifier = LegalBERTClassifier(use_onnx=False)
                
                # Warmup
                classifier.predict({}, "warmup text")
                
                profiler = DeviceProfiler()
                profiler.start()
                
                runs = self.bench_cfg["transformer_benchmark"]["runs"]
                for _ in range(runs):
                    for sample in text_samples:
                        classifier.predict({}, sample)
                        
                metrics = profiler.stop()
                
                results["legalbert_pytorch"] = {
                    "status": "Available",
                    "type": "Transformer (PyTorch)",
                    "latency_ms": metrics["latency_ms"] / (runs * len(text_samples)),
                    "memory_mb": metrics["memory_mb"],
                    "throughput": (runs * len(text_samples)) / (metrics["latency_ms"] / 1000.0)
                }
            except Exception as e:
                results["legalbert_pytorch"] = {
                    "status": "Unavailable",
                    "reason": f"PyTorch execution failed: {e}"
                }
        else:
            results["legalbert_pytorch"] = {
                "status": "Unavailable",
                "reason": f"PyTorch weights not found at {pt_path}"
            }

        # 2. ONNX benchmark
        onnx_path = os.path.join(artifacts_dir, "onnx", "transformer.onnx")
        if not os.path.exists(onnx_path):
            # Check legacy folder fallback
            onnx_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dl_models", "model.onnx")
            
        if os.path.exists(onnx_path):
            try:
                from services.deep_learning.predictor import LegalBERTClassifier
                classifier = LegalBERTClassifier(use_onnx=True)
                
                # Warmup
                classifier.predict({}, "warmup text")
                
                profiler = DeviceProfiler()
                profiler.start()
                
                runs = self.bench_cfg["transformer_benchmark"]["runs"]
                for _ in range(runs):
                    for sample in text_samples:
                        classifier.predict({}, sample)
                        
                metrics = profiler.stop()
                
                results["legalbert_onnx"] = {
                    "status": "Available",
                    "type": "Transformer (ONNX)",
                    "latency_ms": metrics["latency_ms"] / (runs * len(text_samples)),
                    "memory_mb": metrics["memory_mb"],
                    "throughput": (runs * len(text_samples)) / (metrics["latency_ms"] / 1000.0)
                }
            except Exception as e:
                results["legalbert_onnx"] = {
                    "status": "Unavailable",
                    "reason": f"ONNX execution failed: {e}"
                }
        else:
            results["legalbert_onnx"] = {
                "status": "Unavailable",
                "reason": f"ONNX model file not found at {onnx_path}"
            }
            
        return results
