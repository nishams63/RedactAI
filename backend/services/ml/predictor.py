"""
Predictor — Level 1 Machine Learning Baseline
Loads persisted artifacts and performs inference on single documents.
"""
import logging
import os
import time
from typing import Dict, Any, List

import joblib
from sqlalchemy.orm import Session

from models.ml_models import MLPrediction
from services.ml.config import SENSITIVITY_CLASSES
from services.ml.feature_extractor import FeatureExtractor
from services.ml.preprocessor import DataPreprocessor
from services.ml.dataset_generator import ML_MODELS_DIR

logger = logging.getLogger("redactai.ml.predictor")


class MLPredictor:
    """Performs inference using trained models."""

    def __init__(self, db: Session):
        self.db = db
        self.feature_extractor = FeatureExtractor(db)
        self.preprocessor = DataPreprocessor()
        self.model = None

    def predict_sensitivity(self, document_id: str) -> Dict[str, Any]:
        """
        Run inference on a single processed document.
        
        1. Extract features from DB
        2. Load model & preprocessing artifacts
        3. Transform & predict
        4. Save prediction record to DB
        """
        start_time = time.time()
        
        # ─── 1. Extract Features ──────────────────────────────────────────
        features = self.feature_extractor.extract(document_id)
        if not features:
            raise ValueError(f"Could not extract features for document {document_id}")

        # ─── 2. Load Model & Artifacts ────────────────────────────────────
        model_path = os.path.join(ML_MODELS_DIR, "best_model.joblib")
        if not os.path.exists(model_path):
            raise FileNotFoundError("ML model not trained. Call /ml/train first.")
            
        if self.model is None:
            self.model = joblib.load(model_path)
            # The preprocessor lazy-loads its own artifacts (scaler, imputer, etc.)
            self.preprocessor._load_artifacts()

        # ─── 3. Transform & Predict ───────────────────────────────────────
        # Scale features
        X_scaled = self.preprocessor.transform(features)

        # Predict class
        y_pred_encoded = self.model.predict(X_scaled)[0]
        predicted_class = self.preprocessor.inverse_label(y_pred_encoded)

        # Predict probabilities
        probabilities = {}
        confidence = 0.0
        if hasattr(self.model, "predict_proba"):
            probs = self.model.predict_proba(X_scaled)[0]
            confidence = float(max(probs))
            for i, p in enumerate(probs):
                class_name = self.preprocessor.inverse_label(i)
                probabilities[class_name] = float(p)
        else:
            # Fallback for models without predict_proba
            confidence = 1.0
            probabilities = {c: (1.0 if c == predicted_class else 0.0) for c in SENSITIVITY_CLASSES}

        # Explainability: Top contributing features for this prediction
        # For a single sample, we approximate this using global feature importance
        # scaled by the feature's actual value for this document.
        importances = []
        if hasattr(self.model, "feature_importances_"):
            scores = self.model.feature_importances_
        elif hasattr(self.model, "coef_"):
            # Multi-class LR
            scores = abs(self.model.coef_).mean(axis=0)
        else:
            scores = [0.0] * len(self.preprocessor.feature_names)

        for name, score in zip(self.preprocessor.feature_names, scores):
            importances.append({"name": name, "importance": float(score)})
        
        importances.sort(key=lambda x: x["importance"], reverse=True)
        top_features = importances[:5]

        inference_time_ms = (time.time() - start_time) * 1000

        model_name = self.model.__class__.__name__

        # ─── 4. Save Prediction ──────────────────────────────────────────
        prediction_record = MLPrediction(
            document_id=document_id,
            predicted_class=predicted_class,
            confidence=confidence,
            probabilities=probabilities,
            top_features=top_features,
            model_version=f"v1.0.0-{model_name.lower()}",
            model_algorithm=model_name,
            inference_time_ms=inference_time_ms
        )
        self.db.add(prediction_record)
        self.db.commit()

        logger.info(f"Predicted '{predicted_class}' (conf: {confidence:.2f}) for doc {document_id}")

        return {
            "predicted_class": predicted_class,
            "confidence": confidence,
            "probabilities": probabilities,
            "top_features": top_features,
            "inference_time_ms": inference_time_ms
        }
