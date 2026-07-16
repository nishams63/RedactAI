import torch
from torch.utils.data import Dataset
import pandas as pd
from typing import Any

from datasets.validators import SENSITIVITY_CLASSES
from datasets.preprocessors import preprocess_legal_text

class TransformerDataset(Dataset):
    """
    Custom PyTorch Dataset for Hugging Face Trainer.
    Avoids requiring the external Hugging Face 'datasets' library.
    """
    def __init__(self, df: pd.DataFrame, tokenizer: Any, max_length: int = 512):
        self.tokenizer = tokenizer
        self.max_length = max_length
        self.texts = df["text"].astype(str).map(preprocess_legal_text).tolist()
        
        raw_labels = df["label"].tolist()
        self.labels = []
        for r in raw_labels:
            if isinstance(r, str) and r in SENSITIVITY_CLASSES:
                self.labels.append(SENSITIVITY_CLASSES.index(r))
            elif isinstance(r, int) and 0 <= r < len(SENSITIVITY_CLASSES):
                self.labels.append(r)
            else:
                self.labels.append(0)

    def __len__(self) -> int:
        return len(self.texts)

    def __getitem__(self, idx: int) -> dict:
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
            "labels": torch.tensor(label, dtype=torch.long)
        }

def build_hf_dataset(df: pd.DataFrame, tokenizer: Any, max_length: int = 512) -> Any:
    """Helper function to build a training-ready Dataset wrapper."""
    return TransformerDataset(df, tokenizer, max_length)
