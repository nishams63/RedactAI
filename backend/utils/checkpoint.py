import os
from typing import Dict, Any

try:
    import torch
except ImportError:
    torch = None

def save_checkpoint(state: Dict[str, Any], filepath: str) -> None:
    """Save PyTorch training checkpoint securely."""
    if torch is None:
        raise ImportError("PyTorch is required to save checkpoints.")
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    torch.save(state, filepath)

def load_checkpoint(filepath: str, map_location: Any = None) -> Dict[str, Any]:
    """Load PyTorch training checkpoint securely."""
    if torch is None:
        raise ImportError("PyTorch is required to load checkpoints.")
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Checkpoint file not found: {filepath}")
    return torch.load(filepath, map_location=map_location)
