from typing import List
import numpy as np
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, confusion_matrix

class MetricsCallback:
    """
    Computes validation classification metrics at the end of each epoch.
    """
    def compute_epoch_metrics(self, y_true: List[int], y_pred: List[int]) -> dict:
        y_true_arr = np.array(y_true)
        y_pred_arr = np.array(y_pred)
        
        acc = accuracy_score(y_true_arr, y_pred_arr)
        precision, recall, f1, _ = precision_recall_fscore_support(
            y_true_arr, y_pred_arr, average="macro", zero_division=0
        )
        
        cm = confusion_matrix(y_true_arr, y_pred_arr).tolist()
        
        return {
            "accuracy": float(acc),
            "precision": float(precision),
            "recall": float(recall),
            "f1_macro": float(f1),
            "confusion_matrix": cm
        }
