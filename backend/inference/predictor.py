import os
import yaml
from typing import Dict, Any, List

import torch
from transformers import AutoTokenizer

from services.deep_learning.interfaces import DocumentClassifier
from services.ml.config import SENSITIVITY_CLASSES

class PyTorchSequenceClassifier(DocumentClassifier):
    """
    Standardized inference wrapper for RNN, LSTM, GRU, and BiLSTM models.
    Conforms to the swappable DocumentClassifier interface.
    """
    def __init__(self, model_type: str, model_path: str, config_dir: str = "configs"):
        self.model_type = model_type.lower()
        self.model_path = model_path
        
        # Load configs
        with open(os.path.join(config_dir, "models.yaml"), "r") as f:
            self.model_cfg = yaml.safe_load(f)
            
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        # Init tokenizer
        tokenizer_name = self.model_cfg["transformer"]["model_name"]
        self.tokenizer = AutoTokenizer.from_pretrained(
            tokenizer_name,
            cache_dir="services/deep_learning/model_cache",
            local_files_only=False
        )
        
        # Load model structure
        seq_cfg = self.model_cfg["sequence_models"]
        if self.model_type == "rnn":
            from models.rnn import RNNClassifier
            self.model = RNNClassifier(**seq_cfg)
        elif self.model_type == "lstm":
            from models.lstm import LSTMClassifier
            self.model = LSTMClassifier(**seq_cfg)
        elif self.model_type == "gru":
            from models.gru import GRUClassifier
            self.model = GRUClassifier(**seq_cfg)
        elif self.model_type == "bilstm":
            from models.bilstm import BiLSTMClassifier
            self.model = BiLSTMClassifier(**seq_cfg)
        else:
            raise ValueError(f"Unknown sequence model: {model_type}")
            
        if os.path.exists(model_path):
            self.model.load_state_dict(torch.load(model_path, map_location=self.device))
        self.model.to(self.device)
        self.model.eval()

    def predict(self, features: Dict[str, Any], text: str) -> Dict[str, Any]:
        results = self.predict_batch([features], [text])
        return results[0]

    def predict_batch(self, batch: List[Dict[str, Any]], texts: List[str]) -> List[Dict[str, Any]]:
        inputs = self.tokenizer(
            texts,
            padding="max_length",
            truncation=True,
            max_length=self.model_cfg["transformer"]["max_length"],
            return_tensors="pt"
        )
        
        input_ids = inputs["input_ids"].to(self.device)
        
        results = []
        with torch.no_grad():
            logits = self.model(input_ids)
            probs = torch.softmax(logits, dim=-1)
            
        for i in range(len(texts)):
            prob_dict = {SENSITIVITY_CLASSES[j]: float(probs[i][j]) for j in range(len(SENSITIVITY_CLASSES))}
            pred_idx = torch.argmax(logits[i]).item()
            predicted_class = SENSITIVITY_CLASSES[pred_idx]
            results.append({
                "predicted_class": predicted_class,
                "confidence": float(probs[i][pred_idx]),
                "probabilities": prob_dict
            })
            
        return results
