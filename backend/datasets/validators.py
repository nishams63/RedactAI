import pandas as pd
from typing import Dict, Any, List

SENSITIVITY_CLASSES = ["Public", "Internal", "Confidential", "Highly Confidential"]

def validate_dataset(df: pd.DataFrame, text_col: str = "text", label_col: str = "label") -> Dict[str, Any]:
    """
    Perform enterprise-grade validation checks on the training dataset.
    Returns a structured validation report.
    """
    report = {
        "valid": True,
        "sample_count": len(df),
        "errors": [],
        "warnings": [],
        "label_distribution": {},
        "missing_count": 0,
        "duplicate_count": 0,
        "class_imbalance": False
    }

    # 1. Empty Check
    if len(df) == 0:
        report["valid"] = False
        report["errors"].append("Dataset is empty. Cannot run training jobs.")
        return report

    # 2. Missing Values Check
    missing_mask = df[text_col].isna() | (df[text_col].astype(str).str.strip() == "")
    missing_count = int(missing_mask.sum())
    report["missing_count"] = missing_count
    if missing_count > 0:
        report["warnings"].append(f"Found {missing_count} rows with missing or empty text values. These will be discarded.")

    # Clean missing rows for subsequent checks
    df_clean = df[~missing_mask].copy()

    # 3. Duplicate Samples Check
    duplicates = int(df_clean.duplicated(subset=[text_col]).sum())
    report["duplicate_count"] = duplicates
    if duplicates > 0:
        report["warnings"].append(f"Found {duplicates} duplicate text samples. Recommending deduplication.")

    # 4. Label Validation
    if label_col in df_clean.columns:
        invalid_labels_mask = ~df_clean[label_col].isin(SENSITIVITY_CLASSES)
        invalid_count = int(invalid_labels_mask.sum())
        if invalid_count > 0:
            report["valid"] = False
            report["errors"].append(f"Found {invalid_count} samples with invalid labels. Valid classes: {SENSITIVITY_CLASSES}")
        
        # Calculate distribution
        counts = df_clean[label_col].value_counts().to_dict()
        report["label_distribution"] = {str(k): int(v) for k, v in counts.items()}
        
        # 5. Class Imbalance Analysis (< 5%)
        total_valid = len(df_clean)
        for label, count in counts.items():
            pct = count / total_valid
            if pct < 0.05:
                report["class_imbalance"] = True
                report["warnings"].append(f"Class '{label}' has severe imbalance ({(pct*100):.1f}% of dataset, less than recommended 5%).")
    else:
        report["valid"] = False
        report["errors"].append(f"Label column '{label_col}' missing from dataset.")

    # 6. Corrupted Records Check
    corrupted_count = 0
    for idx, row in df_clean.iterrows():
        txt = str(row[text_col])
        # Simple heuristic: if text contains > 50% non-ascii or strange control codes
        non_ascii = len([c for c in txt if ord(c) > 127 or ord(c) < 32 and c not in ['\n', '\r', '\t']])
        if len(txt) > 0 and (non_ascii / len(txt)) > 0.5:
            corrupted_count += 1
            
    if corrupted_count > 0:
        report["warnings"].append(f"Found {corrupted_count} potential corrupted records containing high ratios of unreadable glyphs.")

    return report
