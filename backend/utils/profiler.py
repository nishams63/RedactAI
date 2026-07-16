import time
import os
from typing import Dict, Any

try:
    import psutil
except ImportError:
    psutil = None

try:
    import torch
except ImportError:
    torch = None

class DeviceProfiler:
    """Profiles latency, CPU RAM, and GPU memory utilization."""
    
    def __init__(self):
        self.start_time = None
        self.start_memory = None
        
    def start(self) -> None:
        self.start_time = time.time()
        self.start_memory = self.get_memory_usage()
        
    def stop(self) -> Dict[str, float]:
        """Stop profiling and return metrics dictionary."""
        end_time = time.time()
        end_memory = self.get_memory_usage()
        
        latency_ms = (end_time - self.start_time) * 1000.0
        memory_diff_mb = max(0.0, end_memory - self.start_memory)
        
        gpu_mb = 0.0
        if torch is not None and torch.cuda.is_available():
            gpu_mb = torch.cuda.max_memory_allocated() / (1024 * 1024)
            
        return {
            "latency_ms": latency_ms,
            "memory_mb": end_memory,
            "memory_diff_mb": memory_diff_mb,
            "gpu_memory_mb": gpu_mb
        }
        
    def get_memory_usage(self) -> float:
        """Returns process RAM usage in MB."""
        if psutil is not None:
            process = psutil.Process(os.getpid())
            return process.memory_info().rss / (1024 * 1024)
        return 0.0
