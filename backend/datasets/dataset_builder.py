import datetime
import hashlib
from typing import Dict, Any, Tuple
import pandas as pd

from datasets.validators import validate_dataset

def calculate_checksum(df: pd.DataFrame, text_col: str = "text") -> str:
    """Computes an MD5 checksum of the text contents in a dataset."""
    hasher = hashlib.md5()
    for text in df[text_col].astype(str):
        hasher.update(text.encode("utf-8"))
    return hasher.hexdigest()

class DatasetBuilder:
    """
    Decoupled orchestrator to load, preprocess, validate, and version-track datasets.
    """
    @staticmethod
    def prepare_dataset(
        df: pd.DataFrame,
        version: str = "v1.0",
        source: str = "hybrid",
        text_col: str = "text",
        label_col: str = "label"
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Validate, preprocess, and generate version tracking metadata for a dataset.
        """
        # 1. Validate raw data
        validation_report = validate_dataset(df, text_col, label_col)
        if not validation_report["valid"]:
            raise ValueError(f"Dataset validation failed: {validation_report['errors']}")
            
        # 2. Filter missing labels or text
        df_clean = df[df[text_col].notna() & (df[text_col].astype(str).str.strip() != "")].copy()
        
        # 3. Compute checksum
        checksum = calculate_checksum(df_clean, text_col)
        
        # 4. Generate Metadata
        metadata = {
            "dataset_version": version,
            "checksum": checksum,
            "label_distribution": validation_report["label_distribution"],
            "sample_count": len(df_clean),
            "source": source,
            "creation_date": datetime.datetime.utcnow().isoformat(),
            "validation_warnings": validation_report["warnings"]
        }
        
        return df_clean, metadata
