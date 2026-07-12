"""
Data Preprocessor — Level 1 Machine Learning Baseline
Handles missing values, encoding, scaling, outlier capping,
and stratified train/test splitting.
"""
import logging
import os
import json
from typing import Dict, Any, Tuple, Optional

import numpy as np
import pandas as pd
import joblib
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import StratifiedShuffleSplit

from services.ml.config import ALL_FEATURE_NAMES, SENSITIVITY_CLASSES

logger = logging.getLogger("redactai.ml.preprocessor")

ML_MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "ml_models")


class DataPreprocessor:
    """End-to-end data preprocessing pipeline."""

    def __init__(self):
        self.scaler: Optional[StandardScaler] = None
        self.label_encoder: Optional[LabelEncoder] = None
        self.imputer: Optional[SimpleImputer] = None
        self.feature_names = ALL_FEATURE_NAMES.copy()

    def fit_transform(
        self,
        df: pd.DataFrame,
        test_size: float = 0.2,
        random_seed: int = 42,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, Dict[str, Any]]:
        """
        Full preprocessing pipeline: impute → cap outliers → scale → split.

        Args:
            df: DataFrame with features + sensitivity_label column.
            test_size: Fraction for test set.
            random_seed: Random state for reproducibility.

        Returns:
            (X_train, X_test, y_train, y_test, metadata_dict)
        """
        logger.info(f"Preprocessing dataset: {len(df)} samples, {len(self.feature_names)} features.")

        # ─── Extract feature matrix and labels ─────────────────────
        X = df[self.feature_names].copy()
        y_raw = df["sensitivity_label"].copy()

        # ─── 1. Handle Missing Values ──────────────────────────────
        self.imputer = SimpleImputer(strategy="median")
        X_imputed = pd.DataFrame(
            self.imputer.fit_transform(X),
            columns=self.feature_names,
            index=X.index,
        )
        missing_before = int(X.isnull().sum().sum())
        logger.info(f"Imputed {missing_before} missing values (median strategy).")

        # ─── 2. Outlier Capping (IQR method) ──────────────────────
        outliers_capped = 0
        for col in self.feature_names:
            q1 = X_imputed[col].quantile(0.05)
            q3 = X_imputed[col].quantile(0.95)
            iqr = q3 - q1
            lower = q1 - 1.5 * iqr
            upper = q3 + 1.5 * iqr
            mask = (X_imputed[col] < lower) | (X_imputed[col] > upper)
            outliers_capped += int(mask.sum())
            X_imputed[col] = X_imputed[col].clip(lower, upper)
        logger.info(f"Capped {outliers_capped} outlier values (IQR method).")

        # ─── 3. Feature Scaling ────────────────────────────────────
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X_imputed)
        logger.info("Applied StandardScaler normalization.")

        # ─── 4. Label Encoding ─────────────────────────────────────
        self.label_encoder = LabelEncoder()
        self.label_encoder.fit(SENSITIVITY_CLASSES)
        y_encoded = self.label_encoder.transform(y_raw)
        logger.info(f"Encoded {len(SENSITIVITY_CLASSES)} sensitivity classes.")

        # ─── 5. Stratified Train/Test Split ────────────────────────
        sss = StratifiedShuffleSplit(n_splits=1, test_size=test_size, random_state=random_seed)
        train_idx, test_idx = next(sss.split(X_scaled, y_encoded))

        X_train = X_scaled[train_idx]
        X_test = X_scaled[test_idx]
        y_train = y_encoded[train_idx]
        y_test = y_encoded[test_idx]

        logger.info(f"Split: train={len(X_train)}, test={len(X_test)} (stratified, test_size={test_size}).")

        # ─── 6. Save Preprocessing Artifacts ──────────────────────
        self._save_artifacts()

        metadata = {
            "total_samples": len(df),
            "train_samples": len(X_train),
            "test_samples": len(X_test),
            "feature_count": len(self.feature_names),
            "missing_values_imputed": missing_before,
            "outliers_capped": outliers_capped,
            "test_size": test_size,
            "random_seed": random_seed,
            "classes": SENSITIVITY_CLASSES,
        }

        return X_train, X_test, y_train, y_test, metadata

    def transform(self, features: Dict[str, Any]) -> np.ndarray:
        """
        Transform a single feature vector using fitted preprocessor.

        Args:
            features: Dict of feature_name -> value.

        Returns:
            Scaled numpy array (1, n_features).
        """
        if self.scaler is None or self.imputer is None:
            self._load_artifacts()

        values = [features.get(name, 0) for name in self.feature_names]
        arr = np.array(values).reshape(1, -1)
        arr = self.imputer.transform(arr)
        arr = self.scaler.transform(arr)
        return arr

    def inverse_label(self, encoded: int) -> str:
        """Convert encoded label back to string."""
        if self.label_encoder is None:
            self._load_artifacts()
        return self.label_encoder.inverse_transform([encoded])[0]

    def _save_artifacts(self) -> None:
        """Persist preprocessing objects for reproducible inference."""
        os.makedirs(ML_MODELS_DIR, exist_ok=True)
        joblib.dump(self.scaler, os.path.join(ML_MODELS_DIR, "scaler.joblib"))
        joblib.dump(self.imputer, os.path.join(ML_MODELS_DIR, "imputer.joblib"))
        joblib.dump(self.label_encoder, os.path.join(ML_MODELS_DIR, "label_encoder.joblib"))

        with open(os.path.join(ML_MODELS_DIR, "feature_names.json"), "w") as f:
            json.dump(self.feature_names, f, indent=2)

        logger.info("Saved preprocessing artifacts: scaler, imputer, label_encoder, feature_names.")

    def _load_artifacts(self) -> None:
        """Load persisted preprocessing objects."""
        self.scaler = joblib.load(os.path.join(ML_MODELS_DIR, "scaler.joblib"))
        self.imputer = joblib.load(os.path.join(ML_MODELS_DIR, "imputer.joblib"))
        self.label_encoder = joblib.load(os.path.join(ML_MODELS_DIR, "label_encoder.joblib"))

        with open(os.path.join(ML_MODELS_DIR, "feature_names.json"), "r") as f:
            self.feature_names = json.load(f)

        logger.info("Loaded preprocessing artifacts from disk.")
