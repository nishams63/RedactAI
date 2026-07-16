import os
from utils.seed import set_seed

try:
    import torch
except ImportError:
    torch = None

def make_reproducible(seed: int = 42) -> None:
    """Enforces deterministic behavior in Python, NumPy, and PyTorch (including CUDA)."""
    set_seed(seed)
    if torch is not None:
        # Enforce deterministic algorithm execution
        os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False
        if hasattr(torch, "use_deterministic_algorithms"):
            try:
                torch.use_deterministic_algorithms(True, warn_only=True)
            except Exception:
                pass
