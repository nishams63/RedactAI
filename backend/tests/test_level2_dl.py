import os
import uuid
import pytest
import pandas as pd
from sqlalchemy.orm import Session
from database.session import SessionLocal, Base, engine
import models

# Ensure all database tables exist before tests execute
Base.metadata.create_all(bind=engine)
from training.trainer import SequenceModelTrainer
from experiments.tracker import DLExperimentTracker
from registry.model_registry import ModelRegistryManager
from registry.model_card import ModelCardGenerator
from quantization.quantizer import ModelQuantizer
from benchmarks.sequence_benchmark import SequenceModelBenchmark
from benchmarks.transformer_benchmark import TransformerModelBenchmark
from benchmarks.slm_benchmark import SmallLanguageModelBenchmark

# FastAPI test client imports
from fastapi.testclient import TestClient
from main import app
from models.user import User

client = TestClient(app)

# Seed simple mock dataset for testing
MOCK_DF = pd.DataFrame({
    "text": [
        "This is a public press release document.",
        "This agreement is internal only for review draft.",
        "Confidential NDA agreement between TCS and Microsoft.",
        "Highly confidential passport secret details."
    ],
    "label": ["Public", "Internal", "Confidential", "Highly Confidential"]
})

def test_1_sequence_models_training():
    """Verify PyTorch sequence model training and ONNX export workflows."""
    trainer = SequenceModelTrainer()
    report = trainer.train_sequence_model(
        dataset_df=MOCK_DF,
        model_type="lstm",
        dataset_version="v_test_1"
    )
    
    assert report["status"] == "success"
    assert report["model_type"] == "lstm"
    assert "val_loss" in report
    assert "val_accuracy" in report
    assert report["onnx_path"] is not None
    assert os.path.exists(report["model_save_path"])

def test_2_transformer_model_training():
    """Verify Hugging Face trainer workflows with early stopping and checkpoints."""
    trainer = SequenceModelTrainer()
    report = trainer.train_transformer_model(
        dataset_df=MOCK_DF,
        dataset_version="v_test_2"
    )
    
    assert report["status"] == "success"
    assert report["model_type"] == "transformer"
    assert "val_loss" in report
    assert "val_accuracy" in report
    assert os.path.exists(report["model_save_path"])

def test_3_experiment_tracking():
    """Verify enterprise experiment tracker logs training parameters and metrics."""
    db = SessionLocal()
    tracker = DLExperimentTracker(db)
    
    run_id = tracker.start_run(model_name="BiLSTM Classifier", dataset_version="v1.0")
    assert run_id is not None
    
    metrics = {
        "loss": 0.25,
        "accuracy": 0.90,
        "precision": 0.88,
        "recall": 0.89,
        "f1_macro": 0.89,
        "learning_rate": 1e-3,
        "batch_size": 8,
        "epochs": 5,
        "optimizer": "AdamW",
        "training_time": 10.5,
        "hardware": "CPU",
        "random_seed": 42,
        "onnx_export": True
    }
    tracker.log_metrics(run_id, metrics)
    
    runs = tracker.get_experiments()
    assert len(runs) > 0
    matched = [r for r in runs if r.experiment_id == run_id][0]
    assert matched.model_name == "BiLSTM Classifier"
    assert matched.accuracy == 0.90
    assert matched.onnx_export is True
    
    db.delete(matched)
    db.commit()
    db.close()

def test_4_model_registry_and_rollbacks():
    """Verify active model registrations, dynamic deployment swaps, and rollbacks."""
    db = SessionLocal()
    manager = ModelRegistryManager(db)
    
    m1 = manager.register_model(name="LSTM Test", version="1.0.0", parameters={"acc": 0.8})
    m2 = manager.register_model(name="LSTM Test", version="2.0.0", parameters={"acc": 0.9})
    
    assert m2.status == "Active"
    # m1 should be deactivated automatically
    assert m1.status == "Deprecated"
    
    # Deploy version 1.0.0 again
    success = manager.deploy_model(m1.id)
    assert success is True
    assert m1.status == "Active"
    assert m2.status == "Deprecated"
    
    # Rollback
    success = manager.rollback_model(name="LSTM Test", fallback_version="2.0.0")
    assert success is True
    assert m2.status == "Active"
    assert m1.status == "Deprecated"
    
    db.delete(m1)
    db.delete(m2)
    db.commit()
    db.close()

def test_5_benchmarks_profiling():
    """Verify sequence, transformer, and SLM benchmark harnesses."""
    text_samples = ["Analyze this legal text sample."]
    
    # Sequence benchmark
    seq_bench = SequenceModelBenchmark()
    seq_res = seq_bench.run_benchmark(text_samples)
    assert isinstance(seq_res, dict)
    
    # Transformer benchmark
    trans_bench = TransformerModelBenchmark()
    trans_res = trans_bench.run_benchmark(text_samples)
    assert isinstance(trans_res, dict)
    
    # SLM benchmark (safely handles unavailable models)
    slm_bench = SmallLanguageModelBenchmark()
    slm_res = slm_bench.run_benchmark(text_samples)
    assert isinstance(slm_res, dict)

def test_6_quantization_comparison():
    """Verify PyTorch dynamic quantization returns quantized models."""
    from models.lstm import LSTMClassifier
    model = LSTMClassifier(vocab_size=100, embedding_dim=32, hidden_dim=32, output_dim=4)
    
    quantized_model = ModelQuantizer.quantize_pytorch_model(model)
    assert quantized_model is not None
    # Verify quantized layers type
    assert hasattr(quantized_model, "lstm")
