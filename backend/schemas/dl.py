"""Pydantic schemas for Deep Learning API endpoints."""
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class DLTrainRequest(BaseModel):
    epochs: int = Field(3, ge=1, le=20, description="Number of epochs to train")
    batch_size: int = Field(8, ge=1, le=64, description="Inference/training batch size")
    learning_rate: float = Field(2e-5, ge=1e-6, le=1e-3, description="Adam optimizer learning rate")
    dataset_size: int = Field(5000, description="Size of the hybrid training set")


class DLMetrics(BaseModel):
    accuracy: float
    precision_macro: float = Field(..., alias="precision_macro")
    recall_macro: float = Field(..., alias="recall_macro")
    f1_macro: float = Field(..., alias="f1_macro")
    throughput: float
    latency_ms: float
    memory_mb: float


class DLTrainResponse(BaseModel):
    model_name: str
    pytorch_version: str
    dataset_version: str
    dataset_hash: str
    epochs: int
    batch_size: int
    learning_rate: float
    training_time_seconds: float
    metrics: DLMetrics
    reproducibility: Dict[str, Any]


class ModelPerformanceItem(BaseModel):
    type: str
    accuracy: float
    precision: float
    recall: float
    f1: float
    latency_ms: float
    throughput: float
    memory_mb: float
    training_time_seconds: float
    model_size_mb: float
    inference_time_ms: float


class DLComparisonResponse(BaseModel):
    best_model_ml: str
    best_model_dl: str
    models: Dict[str, ModelPerformanceItem]


class DLInferenceResponse(BaseModel):
    winning_class: str
    winning_model: str
    confidence: float
    agreement: bool
    inference_time_ms: float


class DLProgressResponse(BaseModel):
    current_epoch: int
    total_epochs: int
    current_loss: float
    val_accuracy: float
    estimated_time_remaining: float
    status: str
