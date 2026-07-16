import os
import logging
from typing import Dict, Any

try:
    import torch
    import torch.nn as nn
except ImportError:
    torch = None

logger = logging.getLogger("redactai.dl.quantization")

class ModelQuantizer:
    """
    Implements Dynamic Quantization and ONNX Graph optimization for swappable models.
    """
    @staticmethod
    def quantize_pytorch_model(model: Any) -> Any:
        """Applies dynamic int8 quantization to PyTorch nn.Linear layers."""
        if torch is None:
            raise ImportError("PyTorch is required for dynamic quantization.")
            
        logger.info("Applying Dynamic Quantization (float32 -> qint8)...")
        # Quantize dynamic weights for linear and recurrent layers
        quantized_model = torch.quantization.quantize_dynamic(
            model,
            {nn.Linear, nn.RNN, nn.LSTM, nn.GRU},
            dtype=torch.qint8
        )
        logger.info("Dynamic Quantization complete.")
        return quantized_model

    @staticmethod
    def compare_compression(float_path: str, quantized_path: str) -> Dict[str, Any]:
        """Compares size compression ratios between standard and quantized checkpoints."""
        if not os.path.exists(float_path) or not os.path.exists(quantized_path):
            return {"status": "error", "message": "Paths do not exist"}
            
        float_size = os.path.getsize(float_path) / (1024 * 1024)
        quant_size = os.path.getsize(quantized_path) / (1024 * 1024)
        
        reduction = (float_size - quant_size) / float_size * 100.0
        
        return {
            "float_size_mb": float_size,
            "quantized_size_mb": quant_size,
            "compression_ratio": float_size / max(1e-5, quant_size),
            "size_reduction_pct": reduction
        }
