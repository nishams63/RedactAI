"""
Inference Engine — Level 2 Deep Learning Enhancement
Aggregates predictions from ML and DL pipelines, runs comparison audits,
and stores the final consensus sensitivity prediction.
"""
import logging
import time
from typing import Dict, Any

from sqlalchemy.orm import Session

from models.ml_models import MLPrediction
from services.ml.predictor import MLPredictor
from services.deep_learning.model_registry import DLModelRegistry

logger = logging.getLogger("redactai.dl.inference")


class DLInferenceEngine:
    """Runs combined ML/DL predictions and aggregates them."""

    def __init__(self, db: Session):
        self.db = db
        self.ml_predictor = MLPredictor(db)

    def predict_consensus(
        self,
        document_id: Any,
        text: str,
        dl_model_type: str = "nlpaueb/legal-bert-base-uncased",
    ) -> Dict[str, Any]:
        """
        Runs both ML and DL pipelines, compares confidence,
        selects the consensus prediction, and stores metadata in DB.
        """
        import uuid
        if isinstance(document_id, str):
            document_id = uuid.UUID(document_id)
        start_time = time.time()
        
        # 1. Get ML Prediction
        try:
            ml_res = self.ml_predictor.predict_sensitivity(document_id)
        except Exception as e:
            logger.warning(f"ML prediction failed: {e}. Defaulting to dummy ML.")
            ml_res = {
                "predicted_class": "Internal",
                "confidence": 0.5,
                "probabilities": {}
            }

        # 2. Get DL Prediction
        try:
            # Instantiate classifier via dynamic registry
            dl_classifier = DLModelRegistry.get_classifier(dl_model_type)
            
            # Extract ML features for classifier context (needed for layout-based or multimodal classifiers)
            from services.ml.feature_extractor import FeatureExtractor
            features = FeatureExtractor(self.db).extract(document_id) or {}
            
            dl_res = dl_classifier.predict(features, text)
        except Exception as e:
            logger.error(f"DL prediction failed for document {document_id}: {e}", exc_info=True)
            # Failover: if DL fails (e.g. weights not downloaded), use ML prediction
            dl_res = {
                "predicted_class": ml_res["predicted_class"],
                "confidence": ml_res["confidence"],
                "probabilities": ml_res["probabilities"],
                "error": str(e)
            }

        # 3. Consensus Logic
        from services.ml.config import apply_sensitivity_label
        
        # Get features
        from services.ml.feature_extractor import FeatureExtractor
        features = FeatureExtractor(self.db).extract(document_id) or {}
        
        # Override the confidence in features using ML and DL model outputs to make it dynamic
        features["avg_confidence"] = max(ml_res.get("confidence", 1.0), dl_res.get("confidence", 1.0))
        
        # Apply weighted policy engine
        winning_class = apply_sensitivity_label(features)
        winning_confidence = features["avg_confidence"]
        
        agreement = ml_res["predicted_class"] == dl_res["predicted_class"]
        
        if winning_class == ml_res["predicted_class"] and winning_class == dl_res["predicted_class"]:
            winning_model = "Consensus (ML & DL)"
        elif winning_class == dl_res["predicted_class"]:
            winning_model = f"Deep Learning ({dl_model_type})"
        elif winning_class == ml_res["predicted_class"]:
            winning_model = f"ML Baseline ({ml_res.get('model_algorithm', 'RandomForest')})"
        else:
            winning_model = "Policy Engine (Weighted Content Rules)"

        inference_time_ms = (time.time() - start_time) * 1000

        # Note: In Level 1, we saved to the MLPrediction table.
        # For Level 2, we update or insert a prediction record representing the consensus.
        # We also store agreement metadata inside probabilities/JSON fields.
        pred_record = self.db.query(MLPrediction).filter(
            MLPrediction.document_id == document_id
        ).first()

        if not pred_record:
            pred_record = MLPrediction(document_id=document_id)
            self.db.add(pred_record)

        pred_record.predicted_class = winning_class
        pred_record.confidence = winning_confidence
        pred_record.model_version = f"v2.0.0-consensus"
        pred_record.model_algorithm = winning_model
        pred_record.inference_time_ms = inference_time_ms
        pred_record.probabilities = {
            "ml_prediction": ml_res["predicted_class"],
            "ml_confidence": ml_res["confidence"],
            "dl_prediction": dl_res["predicted_class"],
            "dl_confidence": dl_res["confidence"],
            "agreement": agreement
        }
        
        self.db.commit()
        logger.info(f"Consensus prediction: {winning_class} ({winning_model})")

        return {
            "winning_class": winning_class,
            "winning_model": winning_model,
            "confidence": winning_confidence,
            "ml_prediction": ml_res,
            "dl_prediction": dl_res,
            "agreement": agreement,
            "inference_time_ms": inference_time_ms
        }
