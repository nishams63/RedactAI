"""Pydantic schemas for ML endpoints."""
from datetime import datetime
from uuid import UUID
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field


class TrainRequest(BaseModel):
    dataset_size: int = Field(5000, description="Total size of the hybrid dataset to generate")


class FeatureImportanceItem(BaseModel):
    name: str
    importance: float


class PredictionResponse(BaseModel):
    predicted_class: str
    confidence: float
    probabilities: Dict[str, float]
    top_features: List[FeatureImportanceItem]
    inference_time_ms: float


class ModelMetrics(BaseModel):
    accuracy: float
    precision_macro: float
    recall_macro: float
    f1_macro: float
    roc_auc: Optional[float]


class ModelPerformance(BaseModel):
    training_time_seconds: float
    inference_time_ms_per_sample: float


class ModelResultSchema(BaseModel):
    version: str
    metrics: ModelMetrics
    performance: ModelPerformance
    best_params: Dict[str, Any]
    confusion_matrix: List[List[int]]
    cv_scores: List[float]
    feature_importance: List[List[Any]]  # [["feature_name", score], ...]


class DatasetMetadata(BaseModel):
    total_samples: int
    train_samples: int
    test_samples: int
    feature_count: int
    classes: List[str]


class TrainResponse(BaseModel):
    status: str
    experiment_id: str
    best_model: str
    metrics: ModelMetrics
    dataset: DatasetMetadata
    models: Dict[str, ModelResultSchema]


class RegisteredModelInfo(BaseModel):
    id: UUID
    name: str
    type: str
    version: str
    status: str
    parameters: Dict[str, Any]
    created_at: datetime

    model_config = {"from_attributes": True}


class EvaluationResponse(BaseModel):
    best_model: str
    dataset_metadata: DatasetMetadata
    models: Dict[str, ModelResultSchema]
    timestamp: datetime


class ExperimentResponse(BaseModel):
    id: UUID
    experiment_name: str
    dataset_version: Optional[str]
    best_algorithm: Optional[str]
    best_f1: Optional[float]
    best_accuracy: Optional[float]
    total_training_time_seconds: Optional[float]
    status: str
    created_at: datetime
    completed_at: Optional[datetime]

    model_config = {"from_attributes": True}
