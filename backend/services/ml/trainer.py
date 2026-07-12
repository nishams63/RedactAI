"""
Trainer — Level 1 Machine Learning Baseline
Handles dataset loading, model training, hyperparameter tuning (GridSearchCV),
evaluation, and MLOps experiment tracking.
"""
import logging
import os
import json
import time
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

import pandas as pd
import numpy as np
import joblib

from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.model_selection import GridSearchCV
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, confusion_matrix, classification_report
)
from sqlalchemy.orm import Session

from models.ai_models import AIModel
from models.ml_models import (
    TrainingDataset, ModelEvaluation, FeatureImportance, ExperimentRun
)
from services.ml.config import (
    ALL_FEATURE_NAMES, HYPERPARAMETER_GRIDS, MODEL_FRAMEWORK, SENSITIVITY_CLASSES
)
from services.ml.dataset_generator import DatasetGenerator, ML_MODELS_DIR
from services.ml.preprocessor import DataPreprocessor

logger = logging.getLogger("redactai.ml.trainer")

# Try to import XGBoost, fallback if not available
try:
    from xgboost import XGBClassifier
    XGB_AVAILABLE = True
except ImportError:
    logger.warning("xgboost package not found. XGBoost model will be skipped. Falling back to GradientBoosting.")
    XGB_AVAILABLE = False


class MLTrainer:
    """End-to-end ML training and evaluation pipeline."""

    def __init__(self, db: Session):
        self.db = db

    def train_models(self, dataset_size: int = 5000) -> Dict[str, Any]:
        """
        Run the complete training pipeline.
        
        1. Generate/Load Dataset
        2. Preprocess
        3. Create Experiment Run
        4. Train & Tune (LR, RF, GB, XGB)
        5. Evaluate
        6. Select Best Model
        7. Persist & Register Artifacts
        """
        start_time = time.time()
        logger.info(f"Starting ML training pipeline (target dataset_size={dataset_size})")

        # ─── 1. Generate Dataset ─────────────────────────────────────────
        generator = DatasetGenerator(self.db)
        dataset_meta = generator.generate(total_size=dataset_size)
        
        df = pd.read_csv(dataset_meta["file_path"])
        dataset_record = self.db.query(TrainingDataset).filter(
            TrainingDataset.id == dataset_meta["dataset_id"]
        ).first()

        # ─── 2. Initialize Experiment Tracking ───────────────────────────
        experiment = ExperimentRun(
            experiment_name=f"baseline_run_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            dataset_id=dataset_record.id,
            dataset_version=dataset_record.dataset_version,
            status="RUNNING",
        )
        self.db.add(experiment)
        self.db.commit()

        try:
            # ─── 3. Preprocessing ──────────────────────────────────────────
            preprocessor = DataPreprocessor()
            X_train, X_test, y_train, y_test, prep_meta = preprocessor.fit_transform(df)

            # ─── 4. Model Selection & Tuning ──────────────────────────────
            models_to_train = {
                "LogisticRegression": LogisticRegression(random_state=42),
                "RandomForest": RandomForestClassifier(random_state=42),
                "GradientBoosting": GradientBoostingClassifier(random_state=42),
            }
            if XGB_AVAILABLE:
                models_to_train["XGBoost"] = XGBClassifier(
                    random_state=42, use_label_encoder=False, eval_metric="mlogloss"
                )

            results: Dict[str, Dict[str, Any]] = {}
            best_model_name = None
            best_f1_score = -1.0
            best_model_obj = None
            total_models_trained = 0

            # Train each model using GridSearchCV
            for model_name, base_model in models_to_train.items():
                logger.info(f"Training and tuning {model_name}...")
                param_grid = HYPERPARAMETER_GRIDS.get(model_name, {})
                
                grid_search = GridSearchCV(
                    estimator=base_model,
                    param_grid=param_grid,
                    cv=5,
                    scoring="f1_macro",
                    n_jobs=-1,  # Use all available cores
                    verbose=1
                )

                train_start = time.time()
                grid_search.fit(X_train, y_train)
                train_end = time.time()
                train_duration = train_end - train_start

                best_estimator = grid_search.best_estimator_
                total_models_trained += len(grid_search.cv_results_['params'])

                # ─── 5. Evaluation ─────────────────────────────────────────
                inf_start = time.time()
                y_pred = best_estimator.predict(X_test)
                y_prob = best_estimator.predict_proba(X_test) if hasattr(best_estimator, "predict_proba") else None
                inf_end = time.time()
                inference_time_ms = ((inf_end - inf_start) / len(X_test)) * 1000

                # Metrics
                acc = accuracy_score(y_test, y_pred)
                prec = precision_score(y_test, y_pred, average="macro", zero_division=0)
                rec = recall_score(y_test, y_pred, average="macro", zero_division=0)
                f1 = f1_score(y_test, y_pred, average="macro", zero_division=0)
                
                roc_auc = None
                if y_prob is not None:
                    try:
                        roc_auc = roc_auc_score(y_test, y_prob, multi_class="ovr", average="macro")
                    except Exception as e:
                        logger.warning(f"Could not compute ROC-AUC for {model_name}: {e}")

                all_labels = list(range(len(SENSITIVITY_CLASSES)))
                conf_matrix = confusion_matrix(y_test, y_pred, labels=all_labels).tolist()
                class_report = classification_report(y_test, y_pred, labels=all_labels, target_names=SENSITIVITY_CLASSES, output_dict=True, zero_division=0)

                # Feature Importance
                importances = self._extract_feature_importance(best_estimator, model_name, preprocessor.feature_names)

                model_version = f"v1.0.0-{model_name.lower()}"

                results[model_name] = {
                    "version": model_version,
                    "best_params": grid_search.best_params_,
                    "metrics": {
                        "accuracy": acc,
                        "precision_macro": prec,
                        "recall_macro": rec,
                        "f1_macro": f1,
                        "roc_auc": roc_auc,
                    },
                    "performance": {
                        "training_time_seconds": train_duration,
                        "inference_time_ms_per_sample": inference_time_ms,
                    },
                    "confusion_matrix": conf_matrix,
                    "classification_report": class_report,
                    "cv_scores": grid_search.cv_results_['mean_test_score'].tolist(),
                    "feature_importance": importances,
                    "estimator": best_estimator
                }

                # Save evaluation to DB
                evaluation_record = ModelEvaluation(
                    experiment_id=experiment.id,
                    model_name=model_name,
                    algorithm=model_name,
                    version=model_version,
                    accuracy=acc,
                    precision_macro=prec,
                    recall_macro=rec,
                    f1_macro=f1,
                    roc_auc=roc_auc,
                    confusion_matrix=conf_matrix,
                    classification_report=class_report,
                    cross_val_scores=grid_search.cv_results_['mean_test_score'].tolist(),
                    training_time_seconds=train_duration,
                    inference_time_ms=inference_time_ms,
                    dataset_size=len(df),
                    feature_count=len(ALL_FEATURE_NAMES),
                    hyperparameters=grid_search.best_params_
                )
                self.db.add(evaluation_record)

                # Save top 20 feature importances to DB
                top_features = importances[:20]
                for rank, (fname, score) in enumerate(top_features, 1):
                    # Determine method
                    method = "tree_importance"
                    if model_name == "LogisticRegression":
                        method = "coefficient"
                    
                    fi_record = FeatureImportance(
                        experiment_id=experiment.id,
                        model_name=model_name,
                        feature_name=fname,
                        importance_score=score,
                        rank=rank,
                        method=method
                    )
                    self.db.add(fi_record)

                # Keep track of best model
                if f1 > best_f1_score:
                    best_f1_score = f1
                    best_model_name = model_name
                    best_model_obj = best_estimator

            # ─── 6. Register Best Model ────────────────────────────────────
            logger.info(f"Best model selected: {best_model_name} with F1={best_f1_score:.4f}")
            best_results = results[best_model_name]
            
            # Persist model
            model_path = os.path.join(ML_MODELS_DIR, "best_model.joblib")
            joblib.dump(best_model_obj, model_path)
            
            # Save all evaluation results to JSON for frontend
            results_path = os.path.join(ML_MODELS_DIR, "evaluation_results.json")
            # Create a serializable copy of results without the estimator object
            serializable_results = {}
            for k, v in results.items():
                v_copy = v.copy()
                if "estimator" in v_copy:
                    del v_copy["estimator"]
                serializable_results[k] = v_copy
            
            with open(results_path, "w") as f:
                json.dump({
                    "best_model": best_model_name,
                    "dataset_metadata": prep_meta,
                    "models": serializable_results,
                    "timestamp": datetime.utcnow().isoformat()
                }, f, indent=2)

            # Update best model flag in ModelEvaluation table
            self.db.query(ModelEvaluation).filter(
                ModelEvaluation.experiment_id == experiment.id,
                ModelEvaluation.model_name == best_model_name
            ).update({"is_best_model": True})

            # Register in legacy AIModel table for backwards compatibility
            ai_model = self.db.query(AIModel).filter(AIModel.name == "Sensitivity Predictor").first()
            if not ai_model:
                ai_model = AIModel(
                    name="Sensitivity Predictor",
                    type="CLASSIFICATION"
                )
                self.db.add(ai_model)
            
            ai_model.version = best_results["version"]
            ai_model.status = "ACTIVE"
            ai_model.parameters = {
                "algorithm": best_model_name,
                "framework": MODEL_FRAMEWORK,
                "dataset_version": dataset_record.dataset_version,
                "feature_count": len(ALL_FEATURE_NAMES),
                "output_classes": SENSITIVITY_CLASSES,
                "accuracy": best_results["metrics"]["accuracy"],
                "f1_macro": best_results["metrics"]["f1_macro"],
                "training_time": best_results["performance"]["training_time_seconds"],
                "inference_time": best_results["performance"]["inference_time_ms_per_sample"],
                "hyperparameters": best_results["best_params"]
            }

            # Finalize Experiment
            total_duration = time.time() - start_time
            experiment.best_algorithm = best_model_name
            experiment.best_model_version = best_results["version"]
            experiment.best_f1 = best_f1_score
            experiment.best_accuracy = best_results["metrics"]["accuracy"]
            experiment.total_models_trained = total_models_trained
            experiment.total_training_time_seconds = total_duration
            experiment.hyperparameters_searched = HYPERPARAMETER_GRIDS
            experiment.status = "COMPLETED"
            experiment.completed_at = datetime.utcnow()

            self.db.commit()

            return {
                "status": "success",
                "experiment_id": str(experiment.id),
                "best_model": best_model_name,
                "metrics": best_results["metrics"],
                "dataset": prep_meta,
                "models": serializable_results
            }

        except Exception as e:
            logger.error(f"Training pipeline failed: {str(e)}", exc_info=True)
            experiment.status = "FAILED"
            experiment.notes = str(e)
            experiment.completed_at = datetime.utcnow()
            self.db.commit()
            raise e

    def _extract_feature_importance(
        self, estimator: Any, model_name: str, feature_names: List[str]
    ) -> List[Tuple[str, float]]:
        """Extract and sort feature importances from a trained model."""
        importances = []
        
        if hasattr(estimator, "feature_importances_"):
            # Tree-based models (RF, GB, XGB)
            scores = estimator.feature_importances_
            importances = [(name, float(score)) for name, score in zip(feature_names, scores)]
        
        elif hasattr(estimator, "coef_"):
            # Linear models (Logistic Regression)
            # coef_ shape is (n_classes, n_features). Take mean absolute coefficient across classes.
            scores = np.mean(np.abs(estimator.coef_), axis=0)
            importances = [(name, float(score)) for name, score in zip(feature_names, scores)]
            
        else:
            logger.warning(f"Could not extract feature importance for {model_name}")
            importances = [(name, 0.0) for name in feature_names]

        # Sort descending by importance score
        importances.sort(key=lambda x: x[1], reverse=True)
        return importances
