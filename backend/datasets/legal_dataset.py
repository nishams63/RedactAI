from typing import List, Dict, Any
import pandas as pd

try:
    import torch
    from torch.utils.data import Dataset
except ImportError:
    torch = None
    class Dataset:  # type: ignore
        pass

class LegalSequenceDataset(Dataset):
    """
    Custom PyTorch Dataset for Sequence Models (RNN, LSTM, GRU, BiLSTM).
    Takes a DataFrame, pre-processes the text, and tokenizes it.
    """
    def __init__(self, df: pd.DataFrame, tokenizer: Any, max_length: int = 512):
        if torch is None:
            raise ImportError("PyTorch is required to use LegalSequenceDataset.")
            
        self.tokenizer = tokenizer
        self.max_length = max_length
        
        from datasets.preprocessors import preprocess_legal_text
        from datasets.validators import SENSITIVITY_CLASSES
        
        self.texts = df["text"].astype(str).map(preprocess_legal_text).tolist()
        
        # Convert string labels to integer classes
        raw_labels = df["label"].tolist()
        self.labels = []
        for r in raw_labels:
            if isinstance(r, str) and r in SENSITIVITY_CLASSES:
                self.labels.append(SENSITIVITY_CLASSES.index(r))
            elif isinstance(r, int) and 0 <= r < len(SENSITIVITY_CLASSES):
                self.labels.append(r)
            else:
                self.labels.append(0) # fallback default

    def __len__(self) -> int:
        return len(self.texts)

    def __getitem__(self, idx: int) -> Dict[str, Any]:
        text = self.texts[idx]
        label = self.labels[idx]
        
        inputs = self.tokenizer(
            text,
            padding="max_length",
            truncation=True,
            max_length=self.max_length,
            return_tensors="pt"
        )
        
        return {
            "input_ids": inputs["input_ids"].squeeze(0),
            "attention_mask": inputs["attention_mask"].squeeze(0),
            "label": torch.tensor(label, dtype=torch.long)
        }
