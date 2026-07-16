import os
import sys
import time
import yaml
import logging
from typing import Dict, Any, List, Optional
import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(errors='replace')
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(errors='replace')
    except Exception:
        pass

import torch
import torch.nn as nn
from torch.utils.data import DataLoader

from utils.seed import set_seed
from utils.reproducibility import make_reproducible
from utils.profiler import DeviceProfiler
from datasets.dataset_builder import DatasetBuilder
from datasets.hf_dataset import build_hf_dataset
from datasets.legal_dataset import LegalSequenceDataset

# Callbacks
from training.callbacks.early_stopping import EarlyStoppingCallback
from training.callbacks.checkpoint_callback import CheckpointCallback
from training.callbacks.logging_callback import LoggingCallback
from training.callbacks.metrics_callback import MetricsCallback

logger = logging.getLogger("redactai.dl.training")

# Central artifacts directory path
ARTIFACTS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "artifacts"
)

class TrainingProgressTracker:
    _state = {
        "current_epoch": 0,
        "total_epochs": 0,
        "current_loss": 0.0,
        "val_accuracy": 0.0,
        "estimated_time_remaining": 0.0,
        "status": "idle"
    }

    @classmethod
    def get_progress(cls):
        return cls._state

    @classmethod
    def update(cls, **kwargs):
        cls._state.update(kwargs)

    @classmethod
    def reset(cls):
        cls._state = {
            "current_epoch": 0,
            "total_epochs": 0,
            "current_loss": 0.0,
            "val_accuracy": 0.0,
            "estimated_time_remaining": 0.0,
            "status": "idle"
        }

def log_training_event(message: str, level: str = "INFO"):
    log_dir = os.path.join(ARTIFACTS_DIR, "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, "training.log")
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] [{level}] {message}\n")
    except Exception as e:
        logger.warning(f"Failed to write to training log: {e}")

class SequenceModelTrainer:
    """
    Decoupled model trainer running PyTorch and Hugging Face training loops.
    """
    def __init__(self, config_dir: str = "configs"):
        self.config_dir = config_dir
        
        # Load configs
        with open(os.path.join(config_dir, "training.yaml"), "r") as f:
            self.train_cfg = yaml.safe_load(f)
            
        with open(os.path.join(config_dir, "models.yaml"), "r") as f:
            self.model_cfg = yaml.safe_load(f)
            
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    def train_sequence_model(
        self,
        dataset_df: pd.DataFrame,
        model_type: str, # "rnn", "lstm", "gru", "bilstm"
        dataset_version: str = "v1.0"
    ) -> Dict[str, Any]:
        """
        Runs the training orchestrator for PyTorch Sequence Models.
        """
        make_reproducible(self.train_cfg["seed"])
        
        profiler = DeviceProfiler()
        profiler.start()
        
        # Clean and validate dataset
        df, meta = DatasetBuilder.prepare_dataset(
            dataset_df,
            version=dataset_version,
            source="hybrid"
        )
        
        # CPU fast-dev overrides
        epochs = self.train_cfg["epochs"]
        if self.device.type == "cpu":
            epochs = 1
            df = df.head(40)
            logger.info("Running on CPU: fast dev-mode activated (epochs=1, subset=40).")
            
        # Tokenizer initialization (using legalbert tokenizer to map word ids)
        from transformers import AutoTokenizer
        tokenizer_name = self.model_cfg["transformer"]["model_name"]
        tokenizer = AutoTokenizer.from_pretrained(
            tokenizer_name,
            cache_dir="services/deep_learning/model_cache",
            local_files_only=False
        )
        
        # Split train/val/test
        train_df = df.sample(frac=0.8, random_state=self.train_cfg["seed"])
        val_df = df.drop(train_df.index)
        
        train_dataset = LegalSequenceDataset(train_df, tokenizer, max_length=self.model_cfg["transformer"]["max_length"])
        val_dataset = LegalSequenceDataset(val_df, tokenizer, max_length=self.model_cfg["transformer"]["max_length"])
        
        train_loader = DataLoader(train_dataset, batch_size=self.train_cfg["batch_size"], shuffle=True)
        val_loader = DataLoader(val_dataset, batch_size=self.train_cfg["batch_size"])
        
        # Load sequence model
        model_type_lower = model_type.lower()
        seq_cfg = self.model_cfg["sequence_models"]
        
        if model_type_lower == "rnn":
            from models.rnn import RNNClassifier
            model = RNNClassifier(**seq_cfg)
        elif model_type_lower == "lstm":
            from models.lstm import LSTMClassifier
            model = LSTMClassifier(**seq_cfg)
        elif model_type_lower == "gru":
            from models.gru import GRUClassifier
            model = GRUClassifier(**seq_cfg)
        elif model_type_lower == "bilstm":
            from models.bilstm import BiLSTMClassifier
            model = BiLSTMClassifier(**seq_cfg)
        else:
            raise ValueError(f"Unknown model type: {model_type}")
            
        model.to(self.device)
        
        optimizer = torch.optim.AdamW(
            model.parameters(),
            lr=float(self.train_cfg["learning_rate"]),
            weight_decay=self.train_cfg["weight_decay"]
        )
        criterion = nn.CrossEntropyLoss()
        
        # Setup callbacks
        chk_dir = os.path.join(ARTIFACTS_DIR, "checkpoints", model_type_lower)
        checkpoint_cb = CheckpointCallback(chk_dir)
        early_stop_cb = EarlyStoppingCallback(patience=self.train_cfg["early_stopping_patience"])
        logging_cb = LoggingCallback()
        metrics_cb = MetricsCallback()
        
        history = {"train_loss": [], "val_loss": [], "val_acc": [], "val_f1": []}
        
        start_time = time.time()
        TrainingProgressTracker.reset()
        TrainingProgressTracker.update(
            current_epoch=0,
            total_epochs=epochs,
            current_loss=0.0,
            val_accuracy=0.0,
            estimated_time_remaining=0.0,
            status="Training"
        )
        log_training_event(f"Starting sequence model training for {model_type.upper()} Classifier. Total epochs: {epochs}.")
        
        for epoch in range(1, epochs + 1):
            model.train()
            train_loss = 0.0
            
            for step, batch in enumerate(train_loader):
                optimizer.zero_grad()
                
                input_ids = batch["input_ids"].to(self.device)
                labels = batch["label"].to(self.device)
                
                logits = model(input_ids)
                loss = criterion(logits, labels)
                
                loss.backward()
                nn.utils.clip_grad_norm_(model.parameters(), max_norm=float(self.train_cfg["max_grad_norm"]))
                optimizer.step()
                
                train_loss += loss.item()
                logging_cb.on_step(step, loss.item())
                
            train_loss /= len(train_loader)
            
            # Validation
            model.eval()
            val_loss = 0.0
            y_true, y_pred = [], []
            
            with torch.no_grad():
                for batch in val_loader:
                    input_ids = batch["input_ids"].to(self.device)
                    labels = batch["label"].to(self.device)
                    
                    logits = model(input_ids)
                    loss = criterion(logits, labels)
                    val_loss += loss.item()
                    
                    _, preds = torch.max(logits, dim=1)
                    y_true.extend(labels.cpu().tolist())
                    y_pred.extend(preds.cpu().tolist())
                    
            val_loss /= len(val_loader)
            val_metrics = metrics_cb.compute_epoch_metrics(y_true, y_pred)
            
            # Save history
            history["train_loss"].append(train_loss)
            history["val_loss"].append(val_loss)
            history["val_acc"].append(val_metrics["accuracy"])
            history["val_f1"].append(val_metrics["f1_macro"])
            
            # Calculate remaining time
            elapsed = time.time() - start_time
            avg_epoch_time = elapsed / epoch
            remaining_time = avg_epoch_time * (epochs - epoch)
            
            TrainingProgressTracker.update(
                current_epoch=epoch,
                current_loss=float(train_loss),
                val_accuracy=float(val_metrics["accuracy"]),
                estimated_time_remaining=float(remaining_time)
            )
            
            log_training_event(
                f"Epoch {epoch}/{epochs} completed. Train Loss: {train_loss:.4f}, Val Loss: {val_loss:.4f}, Val Accuracy: {val_metrics['accuracy']:.4f}, Val F1: {val_metrics['f1_macro']:.4f}. LR: {self.train_cfg['learning_rate']}"
            )
            
            logging_cb.on_epoch_end(epoch, train_loss, val_loss, val_metrics)
            checkpoint_cb.on_epoch_end(epoch, model, optimizer, val_loss, val_metrics)
            
            # Log checkpoint saves
            chk_path = os.path.join(chk_dir, f"checkpoint_epoch_{epoch}.pt")
            if checkpoint_cb.best_val_loss is None or val_loss < checkpoint_cb.best_val_loss:
                log_training_event(f"Saved best checkpoint for epoch {epoch} to {chk_path}")
            
            if early_stop_cb.on_epoch_end(epoch, val_loss):
                logger.info("Early stopping triggered. Halting training.")
                log_training_event(f"Early stopping triggered at epoch {epoch}.", level="WARNING")
                break
                
        metrics = profiler.stop()
        logging_cb.on_training_end(metrics["latency_ms"] / 1000.0)
        
        # Load best model checkpoint before export or return
        best_path = os.path.join(chk_dir, "best_model.pt")
        if os.path.exists(best_path):
            chk = torch.load(best_path, map_location=self.device)
            model.load_state_dict(chk["model_state_dict"])
            
        # Export weights to artifacts/models
        model_save_path = os.path.join(ARTIFACTS_DIR, "models", f"{model_type_lower}.pt")
        os.makedirs(os.path.dirname(model_save_path), exist_ok=True)
        torch.save(model.state_dict(), model_save_path)
        log_training_event(f"Saved best model weights to {model_save_path}")
        
        # Export to ONNX if possible
        onnx_path = os.path.join(ARTIFACTS_DIR, "onnx", f"{model_type_lower}.onnx")
        os.makedirs(os.path.dirname(onnx_path), exist_ok=True)
        try:
            dummy_input = torch.zeros((1, self.model_cfg["transformer"]["max_length"]), dtype=torch.long).to(self.device)
            torch.onnx.export(
                model,
                dummy_input,
                onnx_path,
                input_names=["input"],
                output_names=["output"],
                dynamic_axes={"input": {0: "batch_size"}, "output": {0: "batch_size"}},
                opset_version=14
            )
            onnx_available = True
            log_training_event(f"Successfully exported ONNX model to {onnx_path}")
        except Exception as e:
            err_msg = str(e).encode('ascii', errors='replace').decode('ascii')
            logger.warning(f"Failed to export sequence model to ONNX: {err_msg}")
            log_training_event(f"Failed to export sequence model to ONNX: {err_msg}", level="WARNING")
            onnx_available = False
            
        TrainingProgressTracker.update(
            status="completed",
            estimated_time_remaining=0.0
        )
        log_training_event(f"Training run for {model_type.upper()} Classifier completed successfully.")
            
        return {
            "model_type": model_type,
            "status": "success",
            "dataset_version": dataset_version,
            "dataset_checksum": meta["checksum"],
            "dataset_metadata": meta,
            "epochs_run": len(history["train_loss"]),
            "train_loss": history["train_loss"][-1],
            "val_loss": history["val_loss"][-1],
            "val_accuracy": history["val_acc"][-1],
            "val_f1": history["val_f1"][-1],
            "metrics": val_metrics,
            "profile": metrics,
            "onnx_path": onnx_path if onnx_available else None,
            "model_save_path": model_save_path
        }

    def train_transformer_model(
        self,
        dataset_df: pd.DataFrame,
        dataset_version: str = "v1.0"
    ) -> Dict[str, Any]:
        """
        Fine-tunes a Hugging Face Transformer (LegalBERT) using the Trainer framework.
        """
        from transformers import (
            AutoModelForSequenceClassification,
            AutoTokenizer,
            Trainer,
            TrainingArguments,
            EarlyStoppingCallback as HFEarlyStoppingCallback,
            DataCollatorWithPadding
        )
        import numpy as np
        from sklearn.metrics import accuracy_score, precision_recall_fscore_support

        make_reproducible(self.train_cfg["seed"])
        profiler = DeviceProfiler()
        profiler.start()

        # 1. Clean and validate dataset
        df, meta = DatasetBuilder.prepare_dataset(
            dataset_df,
            version=dataset_version,
            source="hybrid"
        )

        epochs = self.train_cfg["epochs"]
        if self.device.type == "cpu":
            epochs = 1
            df = df.head(40)
            logger.info("Running on CPU: fast dev-mode activated for Transformer (epochs=1, subset=40).")

        model_name = self.model_cfg["transformer"]["model_name"]
        tokenizer = AutoTokenizer.from_pretrained(
            model_name,
            cache_dir="services/deep_learning/model_cache",
            local_files_only=False
        )

        # Split train/val/test
        train_df = df.sample(frac=0.8, random_state=self.train_cfg["seed"])
        val_df = df.drop(train_df.index)

        # Wrap in HF Dataset
        train_dataset = build_hf_dataset(train_df, tokenizer, max_length=self.model_cfg["transformer"]["max_length"])
        val_dataset = build_hf_dataset(val_df, tokenizer, max_length=self.model_cfg["transformer"]["max_length"])

        model = AutoModelForSequenceClassification.from_pretrained(
            model_name,
            num_labels=self.model_cfg["transformer"]["num_labels"],
            cache_dir="services/deep_learning/model_cache"
        )
        model.to(self.device)

        # Metrics computation for Trainer
        def compute_metrics(eval_pred):
            logits, labels = eval_pred
            preds = np.argmax(logits, axis=-1)
            precision, recall, f1, _ = precision_recall_fscore_support(labels, preds, average="macro", zero_division=0)
            acc = accuracy_score(labels, preds)
            return {
                "accuracy": float(acc),
                "precision": float(precision),
                "recall": float(recall),
                "f1_macro": float(f1)
            }

        chk_dir = os.path.join(ARTIFACTS_DIR, "checkpoints", "transformer")
        os.makedirs(chk_dir, exist_ok=True)

        training_args = TrainingArguments(
            output_dir=chk_dir,
            num_train_epochs=epochs,
            per_device_train_batch_size=self.train_cfg["batch_size"],
            per_device_eval_batch_size=self.train_cfg["batch_size"],
            learning_rate=float(self.train_cfg["learning_rate"]),
            weight_decay=self.train_cfg["weight_decay"],
            eval_strategy="epoch",
            save_strategy="epoch",
            logging_dir=os.path.join(ARTIFACTS_DIR, "reports", "logs"),
            logging_steps=self.train_cfg["logging_steps"],
            load_best_model_at_end=True,
            metric_for_best_model="eval_loss",
            greater_is_better=False,
            disable_tqdm=True,
            use_cpu=(self.device.type == "cpu"),
            report_to="none"
        )

        from transformers import TrainerCallback
        
        class HFProgressTrackingCallback(TrainerCallback):
            def __init__(self, total_epochs, start_time):
                self.total_epochs = total_epochs
                self.start_time = start_time

            def on_epoch_end(self, args, state, control, **kwargs):
                epoch = int(state.epoch)
                elapsed = time.time() - self.start_time
                avg_epoch_time = elapsed / max(epoch, 1)
                remaining_time = avg_epoch_time * (self.total_epochs - epoch)
                
                val_accuracy = 0.0
                current_loss = 0.0
                for log in reversed(state.log_history):
                    if "eval_accuracy" in log and val_accuracy == 0.0:
                        val_accuracy = log["eval_accuracy"]
                    if "loss" in log and current_loss == 0.0:
                        current_loss = log["loss"]
                    if val_accuracy > 0.0 and current_loss > 0.0:
                        break
                
                TrainingProgressTracker.update(
                    current_epoch=epoch,
                    current_loss=float(current_loss),
                    val_accuracy=float(val_accuracy),
                    estimated_time_remaining=float(remaining_time)
                )
                
                log_training_event(
                    f"Epoch {epoch}/{self.total_epochs} completed. Loss: {current_loss:.4f}, Val Accuracy: {val_accuracy:.4f}"
                )
                log_training_event(f"Saved checkpoint at epoch {epoch} inside directory: {chk_dir}")

        start_time = time.time()
        TrainingProgressTracker.reset()
        TrainingProgressTracker.update(
            current_epoch=0,
            total_epochs=epochs,
            current_loss=0.0,
            val_accuracy=0.0,
            estimated_time_remaining=0.0,
            status="Training"
        )
        log_training_event(f"Starting LegalBERT Classifier transformer training. Total epochs: {epochs}.")

        progress_cb = HFProgressTrackingCallback(epochs, start_time)

        import inspect
        trainer_kwargs = {
            "model": model,
            "args": training_args,
            "train_dataset": train_dataset,
            "eval_dataset": val_dataset,
            "data_collator": DataCollatorWithPadding(tokenizer=tokenizer),
            "compute_metrics": compute_metrics,
            "callbacks": [
                HFEarlyStoppingCallback(early_stopping_patience=self.train_cfg["early_stopping_patience"]),
                progress_cb
            ]
        }
        if "processing_class" in inspect.signature(Trainer.__init__).parameters:
            trainer_kwargs["processing_class"] = tokenizer
        else:
            trainer_kwargs["tokenizer"] = tokenizer

        trainer = Trainer(**trainer_kwargs)

        trainer.train()

        # Evaluate best model
        eval_res = trainer.evaluate()

        profile_metrics = profiler.stop()

        # Save model state_dict to artifacts/models
        model_save_path = os.path.join(ARTIFACTS_DIR, "models", "transformer.pt")
        os.makedirs(os.path.dirname(model_save_path), exist_ok=True)
        torch.save(model.state_dict(), model_save_path)
        log_training_event(f"Saved best model weights to {model_save_path}")

        # Export to ONNX
        onnx_path = os.path.join(ARTIFACTS_DIR, "onnx", "transformer.onnx")
        os.makedirs(os.path.dirname(onnx_path), exist_ok=True)
        onnx_available = False
        try:
            model.eval()
            dummy_input = tokenizer("test text", return_tensors="pt", padding="max_length", max_length=self.model_cfg["transformer"]["max_length"])
            input_ids = dummy_input["input_ids"].to(self.device)
            attention_mask = dummy_input["attention_mask"].to(self.device)
            
            torch.onnx.export(
                model,
                (input_ids, attention_mask),
                onnx_path,
                input_names=["input_ids", "attention_mask"],
                output_names=["output"],
                dynamic_axes={
                    "input_ids": {0: "batch_size", 1: "sequence_length"},
                    "attention_mask": {0: "batch_size", 1: "sequence_length"},
                    "output": {0: "batch_size"}
                },
                opset_version=14
            )
            onnx_available = True
            log_training_event(f"Successfully exported ONNX model to {onnx_path}")
        except Exception as e:
            err_msg = str(e).encode('ascii', errors='replace').decode('ascii')
            logger.warning(f"Failed to export transformer to ONNX: {err_msg}")
            log_training_event(f"Failed to export transformer to ONNX: {err_msg}", level="WARNING")
            onnx_available = False
            
        TrainingProgressTracker.update(
            status="completed",
            estimated_time_remaining=0.0
        )
        log_training_event("LegalBERT Classifier training run completed successfully.")

        # Map metrics
        val_metrics = {
            "accuracy": eval_res.get("eval_accuracy", 0.0),
            "precision": eval_res.get("eval_precision", 0.0),
            "recall": eval_res.get("eval_recall", 0.0),
            "f1_macro": eval_res.get("eval_f1_macro", 0.0)
        }

        return {
            "model_type": "transformer",
            "status": "success",
            "dataset_version": dataset_version,
            "dataset_checksum": meta["checksum"],
            "dataset_metadata": meta,
            "epochs_run": eval_res.get("epoch", epochs),
            "train_loss": eval_res.get("train_loss", 0.0),
            "val_loss": eval_res.get("eval_loss", 0.0),
            "val_accuracy": val_metrics["accuracy"],
            "val_f1": val_metrics["f1_macro"],
            "metrics": val_metrics,
            "profile": profile_metrics,
            "onnx_path": onnx_path if onnx_available else None,
            "model_save_path": model_save_path
        }

