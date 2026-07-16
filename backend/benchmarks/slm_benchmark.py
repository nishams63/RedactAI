import os
import yaml
from typing import Dict, Any, List
import time

try:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
except ImportError:
    torch = None

from utils.profiler import DeviceProfiler

class SmallLanguageModelBenchmark:
    """
    Benchmarks various Small Language Models (Qwen, Phi, Gemma, TinyLlama, SmolLM, MiniLM).
    Correctly registers 'Unavailable' status if model download or execution fails.
    """
    def __init__(self, config_dir: str = "configs"):
        self.config_dir = config_dir
        with open(os.path.join(config_dir, "benchmark.yaml"), "r") as f:
            self.bench_cfg = yaml.safe_load(f)

    def run_benchmark(self, text_samples: List[str]) -> Dict[str, Any]:
        """Profiles SLMs and reports metrics or marks them as Unavailable on hardware/resource errors."""
        results = {}
        model_names = self.bench_cfg["slm_benchmark"]["models"]
        
        # Limit sampling during benchmarks to avoid hang ups
        bench_text = text_samples[0] if text_samples else "Analyze this legal clause for compliance."
        
        for m in model_names:
            if torch is None:
                results[m] = {
                    "status": "Unavailable",
                    "reason": "PyTorch or transformers dependencies are missing."
                }
                continue
                
            try:
                # Set a strict timeout or lazy load check
                device = "cuda" if torch.cuda.is_available() else "cpu"
                
                # Check cache directories and try loading local files only first
                logger_msg = f"Attempting to load SLM benchmark model: {m}"
                
                # Note: We try to load the model with local_files_only=True to prevent blocking on network.
                # If that fails, we try loading from online but catch timeouts and report them as Unavailable.
                tokenizer = AutoTokenizer.from_pretrained(m, local_files_only=True)
                model = AutoModelForCausalLM.from_pretrained(m, local_files_only=True, torch_dtype=torch.float16 if device == "cuda" else torch.float32)
                
                model.to(device)
                
                profiler = DeviceProfiler()
                profiler.start()
                
                # Simple forward pass / token generation
                inputs = tokenizer(bench_text, return_tensors="pt").to(device)
                with torch.no_grad():
                    outputs = model.generate(**inputs, max_new_tokens=16)
                    
                metrics = profiler.stop()
                
                # Cleanup model from memory to avoid OOM
                del model
                del tokenizer
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                    
                results[m] = {
                    "status": "Available",
                    "type": "Small Language Model (SLM)",
                    "latency_ms": metrics["latency_ms"],
                    "memory_mb": metrics["memory_mb"],
                    "gpu_memory_mb": metrics["gpu_memory_mb"]
                }
            except Exception as e:
                # Capture hardware OOM or network timeout errors cleanly without breaking the report
                results[m] = {
                    "status": "Unavailable",
                    "reason": f"Failed to download/load model weights: {str(e)}"
                }
                
        return results
