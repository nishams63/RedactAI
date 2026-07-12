"""Machine Learning API endpoints — train, predict, evaluate, and experiment tracking."""
import uuid
import os
import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from dependencies import get_db, get_current_user, check_permissions
from schemas.ml import (
    TrainRequest, TrainResponse, PredictionResponse, RegisteredModelInfo,
    EvaluationResponse, ExperimentResponse
)
from models.user import User
from models.ai_models import AIModel
from models.ml_models import ExperimentRun
from services.ml.trainer import MLTrainer
from services.ml.predictor import MLPredictor
from services.ml.dataset_generator import ML_MODELS_DIR

router = APIRouter(prefix="/ml", tags=["Machine Learning"])


@router.post("/train", response_model=TrainResponse)
def train_ml_pipeline(
    request: TrainRequest,
    current_user: User = Depends(check_permissions(["Admin"])),
    db: Session = Depends(get_db),
):
    """
    Trigger the Level 1 ML pipeline:
    1. Generate hybrid dataset
    2. Run preprocessing
    3. Train & tune LR, RF, GB, XGB models
    4. Select best model & save artifacts
    """
    trainer = MLTrainer(db)
    # Note: For production, this should ideally run in a Celery background task,
    # but for this Level 1 demonstration, we run synchronously to return the 
    # rich comparison response directly to the frontend dashboard.
    result = trainer.train_models(dataset_size=request.dataset_size)
    return result


@router.post("/predict/{document_id}", response_model=PredictionResponse)
def predict_document_sensitivity(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Run ML inference on a specific processed document.
    Requires the document to be in 'Processed' status so features exist.
    """
    predictor = MLPredictor(db)
    try:
        result = predictor.predict_sensitivity(str(document_id))
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")


@router.get("/models", response_model=List[RegisteredModelInfo])
def list_registered_models(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all ML models registered in the database."""
    models = db.query(AIModel).order_by(AIModel.created_at.desc()).all()
    return models


@router.get("/evaluation", response_model=EvaluationResponse)
def get_ml_evaluation(
    current_user: User = Depends(get_current_user),
):
    """Fetch the latest model evaluation metrics and comparison charts."""
    results_path = os.path.join(ML_MODELS_DIR, "evaluation_results.json")
    if not os.path.exists(results_path):
        raise HTTPException(status_code=404, detail="Evaluation results not found. Run training first.")
    
    with open(results_path, "r") as f:
        data = json.load(f)
    return data


@router.get("/experiments", response_model=List[ExperimentResponse])
def list_experiments(
    limit: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List ML training experiment runs (MLOps)."""
    runs = db.query(ExperimentRun).order_by(ExperimentRun.created_at.desc()).limit(limit).all()
    return runs
