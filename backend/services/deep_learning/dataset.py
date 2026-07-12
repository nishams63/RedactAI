"""
PyTorch Dataset & Prep — Level 2 Deep Learning Enhancement
Implements reproducibility seeding, tokenization, layout formatting,
and training/validation/testing splitting.
"""
import random
import logging
import hashlib
from typing import Dict, Any, List, Tuple

import numpy as np
import pandas as pd
import torch
from torch.utils.data import Dataset
from transformers import AutoTokenizer

from services.ml.config import SENSITIVITY_CLASSES

logger = logging.getLogger("redactai.dl.dataset")

# Local cache for HF models/tokenizers
MODEL_CACHE_DIR = "services/deep_learning/model_cache"


def set_reproducibility_seeds(seed: int = 42) -> Dict[str, int]:
    """Set seeds for reproducibility across Python, NumPy, and PyTorch."""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    
    # Ensure deterministic behavior in CUDA
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False

    logger.info(f"Reproducibility seeds set: seed={seed}")
    return {
        "python_seed": seed,
        "numpy_seed": seed,
        "pytorch_seed": seed,
    }


class SensitivityDataset(Dataset):
    """PyTorch dataset preparing text and layout tokens for LegalBERT/LayoutLM."""

    def __init__(
        self,
        texts: List[str],
        bboxes: List[List[List[int]]],  # Bounding boxes per word per page: [[[x1, y1, x2, y2], ...], ...]
        labels: List[int],
        tokenizer_name: str = "nlpaueb/legal-bert-base-uncased",
        max_length: int = 512,
    ):
        self.texts = texts
        self.bboxes = bboxes
        self.labels = labels
        
        # Load tokenizer with local caching
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(
                tokenizer_name,
                cache_dir=MODEL_CACHE_DIR,
                local_files_only=False
            )
        except Exception as e:
            logger.error(f"Failed to load tokenizer {tokenizer_name}: {e}")
            raise e
            
        # Fast Dev Mode on CPU: reduce sequence length to 64 for instant execution
        if not torch.cuda.is_available():
            self.max_length = min(max_length, 64)
        else:
            self.max_length = max_length

    def __len__(self) -> int:
        return len(self.texts)

    def __getitem__(self, idx: int) -> Dict[str, torch.Tensor]:
        text = self.texts[idx]
        label = self.labels[idx]

        # Tokenize text
        encoding = self.tokenizer(
            text,
            padding="max_length",
            truncation=True,
            max_length=self.max_length,
            return_tensors="pt"
        )

        item = {
            "input_ids": encoding["input_ids"].squeeze(0),
            "attention_mask": encoding["attention_mask"].squeeze(0),
            "labels": torch.tensor(label, dtype=torch.long)
        }

        # Include bounding boxes if they are provided (LayoutLM format)
        if self.bboxes and idx < len(self.bboxes):
            # LayoutLM expects boxes scaled to 0-1000 range.
            # Here we pad/truncate bboxes to match token length
            boxes = self.bboxes[idx]
            padded_boxes = [[0, 0, 0, 0]] * self.max_length
            for i, box in enumerate(boxes[:self.max_length]):
                padded_boxes[i] = box
            item["bbox"] = torch.tensor(padded_boxes, dtype=torch.long)

        return item


def prepare_dl_data(
    df: pd.DataFrame,
    tokenizer_name: str = "nlpaueb/legal-bert-base-uncased",
    train_split: float = 0.7,
    val_split: float = 0.15,
    test_split: float = 0.15,
    seed: int = 42,
) -> Tuple[Dataset, Dataset, Dataset, Dict[str, Any]]:
    """
    Splits the hybrid dataset and prepares training, validation, and test PyTorch datasets.
    
    Generates reproducibility metadata and dataset hash.
    """
    set_reproducibility_seeds(seed)
    
    # Check split bounds
    assert abs(train_split + val_split + test_split - 1.0) < 1e-5, "Splits must sum to 1.0"

    # Compute a unique hash of the dataset content for audit trailing
    csv_bytes = df.to_csv(index=False).encode('utf-8')
    dataset_hash = hashlib.sha256(csv_bytes).hexdigest()

    # Extract text and bboxes.
    # Note: df represents structured features + 'sensitivity_label'.
    # In order to simulate document text for DL, we construct text from the counts 
    # of identified legal and risk features if raw text is not present in df,
    # mapping it back to a textual profile representing the document.
    texts = []
    bboxes = []
    
    for _, row in df.iterrows():
        # Reconstruct pseudo-text based on document profiles if raw text not stored in CSV
        if "text" in row:
            texts.append(str(row["text"]))
        else:
            # Generate synthetic legal/risk context strings representing the document
            doc_type = row.get("document_type", "NDA")
            dt = doc_type.lower()
            
            # Inject key semantic terms to match real-world document semantics
            semantic_keywords = ""
            if "medical" in dt:
                semantic_keywords = "HEALTHCARE CLINICAL REPORT Discharge Summary Patient Diagnosis Doctor Hospital"
            elif "court" in dt:
                semantic_keywords = "IN THE HIGH COURT OF DELHI JUDGMENT ORDER LAW Judge Court Order"
            elif "nda" in dt:
                semantic_keywords = "MUTUAL NON-DISCLOSURE AGREEMENT CONFIDENTIAL AGREEMENT Proprietary Information"
            elif "invoice" in dt:
                semantic_keywords = "TAX INVOICE BILL Vendor Bill To Total Amount Due Bank A/c IFSC"
            elif "gov" in dt:
                semantic_keywords = "GOVERNMENT OF INDIA FORM 16 TAX RETRIEVAL Permanent Account Number PAN Aadhaar Card Number"
            elif "employment" in dt:
                semantic_keywords = "EMPLOYMENT AGREEMENT CONTRACT Employee Salary packages Bank Account details"
            elif "service" in dt:
                semantic_keywords = "MASTER SERVICES AGREEMENT Scope migration services terms"
                
            text_profile = f"{semantic_keywords} This {doc_type} contains private legal agreements. "
            text_profile += f"Found critical records: {int(row.get('critical_count', 0))}, high records: {int(row.get('high_count', 0))}. "
            if int(row.get("contains_gov_id", 0)) > 0:
                text_profile += "Includes sensitive government identity information (Aadhaar / Passport). "
            if int(row.get("contains_financial_data", 0)) > 0:
                text_profile += "Includes bank accounts, IFS codes, and transaction records. "
            text_profile += f"Document page count: {int(row.get('num_pages', 1))}. "
            texts.append(text_profile)

        # Reconstruct mock bounding boxes based on entity counts
        # (LayoutLM expects 4-tuples scaled 0-1000)
        num_entities = int(row.get("person_count", 0)) + int(row.get("aadhaar_count", 0))
        box_list = [[100, 100, 200, 120]] * max(num_entities, 1)
        bboxes.append(box_list)

    # Encode Labels
    label_mapping = {label: i for i, label in enumerate(SENSITIVITY_CLASSES)}
    labels = df["sensitivity_label"].map(label_mapping).fillna(0).astype(int).tolist()

    # Split dataset
    n = len(df)
    indices = list(range(n))
    random.shuffle(indices)

    train_end = int(train_split * n)
    val_end = train_end + int(val_split * n)

    train_idx = indices[:train_end]
    val_idx = indices[train_end:val_end]
    test_idx = indices[val_end:]

    # Helper function to slice list by indices
    def slice_list(lst, idxs):
        return [lst[i] for i in idxs]

    train_dataset = SensitivityDataset(
        slice_list(texts, train_idx),
        slice_list(bboxes, train_idx),
        slice_list(labels, train_idx),
        tokenizer_name=tokenizer_name
    )

    val_dataset = SensitivityDataset(
        slice_list(texts, val_idx),
        slice_list(bboxes, val_idx),
        slice_list(labels, val_idx),
        tokenizer_name=tokenizer_name
    )

    test_dataset = SensitivityDataset(
        slice_list(texts, test_idx),
        slice_list(bboxes, test_idx),
        slice_list(labels, test_idx),
        tokenizer_name=tokenizer_name
    )

    metadata = {
        "dataset_hash": dataset_hash,
        "dataset_size": n,
        "train_size": len(train_idx),
        "validation_size": len(val_idx),
        "test_size": len(test_idx),
        "train_split": train_split,
        "validation_split": val_split,
        "test_split": test_split,
        "seed": seed,
    }

    return train_dataset, val_dataset, test_dataset, metadata
