"""
ML Models — Level 1 Machine Learning Baseline
Database tables for training datasets, predictions, evaluations,
feature importance, and experiment tracking.
"""
import uuid
from sqlalchemy import Column, String, Integer, Float, Boolean, Text, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
from database.session import Base


class TrainingDataset(Base):
    """Registry of generated training datasets with full versioning."""
    __tablename__ = "training_datasets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_version = Column(String(50), nullable=False, index=True)
    dataset_source = Column(String(50), nullable=False)          # real, synthetic, hybrid
    generator_version = Column(String(50), nullable=False, default="1.0.0")
    preprocessing_version = Column(String(50), nullable=False, default="1.0.0")
    feature_set_version = Column(String(50), nullable=False, default="1.0.0")
    labeling_rule_version = Column(String(50), nullable=False, default="1.0.0")
    random_seed = Column(Integer, nullable=False, default=42)

    total_samples = Column(Integer, nullable=False)
    real_samples = Column(Integer, nullable=False, default=0)
    synthetic_samples = Column(Integer, nullable=False, default=0)
    feature_count = Column(Integer, nullable=False)
    class_distribution = Column(JSON, nullable=False)            # {"Public": 1200, ...}
    document_type_distribution = Column(JSON, nullable=True)     # {"NDA": 500, ...}
    file_path = Column(String(1024), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    experiments = relationship("ExperimentRun", back_populates="dataset", cascade="all, delete-orphan")


class MLPrediction(Base):
    """Per-document ML sensitivity predictions."""
    __tablename__ = "ml_predictions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    predicted_class = Column(String(50), nullable=False, index=True)
    confidence = Column(Float, nullable=False)
    probabilities = Column(JSON, nullable=True)                  # {"Public": 0.1, "Internal": 0.2, ...}
    top_features = Column(JSON, nullable=True)                   # [{"name": "aadhaar_count", "importance": 0.32}, ...]
    model_version = Column(String(100), nullable=False)
    model_algorithm = Column(String(100), nullable=True)
    inference_time_ms = Column(Float, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    document = relationship("Document", backref="ml_predictions")


class ModelEvaluation(Base):
    """Full evaluation snapshot for a trained model."""
    __tablename__ = "model_evaluations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    experiment_id = Column(UUID(as_uuid=True), ForeignKey("experiment_runs.id", ondelete="CASCADE"), nullable=True)
    model_name = Column(String(255), nullable=False)
    algorithm = Column(String(100), nullable=False)
    version = Column(String(100), nullable=False)

    # Core metrics
    accuracy = Column(Float, nullable=False)
    precision_macro = Column(Float, nullable=False)
    recall_macro = Column(Float, nullable=False)
    f1_macro = Column(Float, nullable=False)
    roc_auc = Column(Float, nullable=True)

    # Detailed reports
    confusion_matrix = Column(JSON, nullable=True)
    classification_report = Column(JSON, nullable=True)
    cross_val_scores = Column(JSON, nullable=True)

    # Performance
    training_time_seconds = Column(Float, nullable=True)
    inference_time_ms = Column(Float, nullable=True)

    # Meta
    dataset_size = Column(Integer, nullable=True)
    feature_count = Column(Integer, nullable=True)
    is_best_model = Column(Boolean, default=False, nullable=False)
    hyperparameters = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    experiment = relationship("ExperimentRun", back_populates="evaluations")


class FeatureImportance(Base):
    """Per-model feature rankings."""
    __tablename__ = "feature_importance"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    experiment_id = Column(UUID(as_uuid=True), ForeignKey("experiment_runs.id", ondelete="CASCADE"), nullable=True)
    model_name = Column(String(255), nullable=False)
    feature_name = Column(String(255), nullable=False)
    importance_score = Column(Float, nullable=False)
    rank = Column(Integer, nullable=False)
    method = Column(String(50), nullable=False)                  # tree_importance, coefficient, shap

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    experiment = relationship("ExperimentRun", back_populates="feature_importances")


class ExperimentRun(Base):
    """MLOps-style experiment log for each training run."""
    __tablename__ = "experiment_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    experiment_name = Column(String(255), nullable=False)
    dataset_id = Column(UUID(as_uuid=True), ForeignKey("training_datasets.id", ondelete="SET NULL"), nullable=True)
    dataset_version = Column(String(50), nullable=True)

    # Best model info
    best_algorithm = Column(String(100), nullable=True)
    best_model_version = Column(String(100), nullable=True)
    best_f1 = Column(Float, nullable=True)
    best_accuracy = Column(Float, nullable=True)

    # Run metadata
    total_models_trained = Column(Integer, nullable=True)
    total_training_time_seconds = Column(Float, nullable=True)
    hyperparameters_searched = Column(JSON, nullable=True)
    notes = Column(Text, nullable=True)
    status = Column(String(50), nullable=False, default="RUNNING")  # RUNNING, COMPLETED, FAILED

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    dataset = relationship("TrainingDataset", back_populates="experiments")
    evaluations = relationship("ModelEvaluation", back_populates="experiment", cascade="all, delete-orphan")
    feature_importances = relationship("FeatureImportance", back_populates="experiment", cascade="all, delete-orphan")


class DLExperiment(Base):
    """Deep Learning / Sequence modeling experiment run tracking registry."""
    __tablename__ = "dl_experiments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    experiment_id = Column(String(100), nullable=False, index=True)
    model_name = Column(String(255), nullable=False)
    dataset_version = Column(String(50), nullable=True)
    learning_rate = Column(Float, nullable=True)
    batch_size = Column(Integer, nullable=True)
    epochs = Column(Integer, nullable=True)
    optimizer = Column(String(50), nullable=True)
    loss = Column(Float, nullable=True)
    accuracy = Column(Float, nullable=True)
    precision = Column(Float, nullable=True)
    recall = Column(Float, nullable=True)
    f1 = Column(Float, nullable=True)
    training_time = Column(Float, nullable=True)
    hardware = Column(String(50), nullable=True)
    random_seed = Column(Integer, nullable=True)
    checkpoint_path = Column(String(500), nullable=True)
    onnx_export = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
