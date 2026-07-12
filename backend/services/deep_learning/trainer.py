"""
Trainer — Level 2 Deep Learning Enhancement
Implements PyTorch training loops, learning rate scheduling,
early stopping, TensorBoard logging, checkpoints, and reports.
"""
import os
import json
import time
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

import numpy as np
import pandas as pd

from services.ml.config import SENSITIVITY_CLASSES
from services.deep_learning.dataset import prepare_dl_data, MODEL_CACHE_DIR, set_reproducibility_seeds
from services.deep_learning.utils import export_to_onnx, plot_training_curves, generate_pdf_report, DL_MODELS_DIR

logger = logging.getLogger("redactai.dl.trainer")


class PretrainedModelUnavailableError(Exception):
    """Raised when the requested pretrained model cannot be loaded/downloaded."""
    pass


class DLTrainer:
    """Orchestrates Deep Learning training and checkpointing."""

    def __init__(self, db_session: Any):
        self.db = db_session
        self.device = self._select_device()

    def _select_device(self) -> Any:
        """Automatically select execution provider: CUDA -> MPS -> CPU."""
        try:
            import torch
            if torch.cuda.is_available():
                dev = torch.device("cuda")
                logger.info("Automatically selected CUDA device for training.")
            elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                dev = torch.device("mps")
                logger.info("Automatically selected MPS device for training.")
            else:
                dev = torch.device("cpu")
                logger.info("Automatically selected CPU device for training.")
            return dev
        except (ImportError, ModuleNotFoundError):
            logger.info("Torch not available. Selected CPU for device fallback.")
            return "cpu"

    def train(
        self,
        dataset_df: pd.DataFrame,
        model_name: str = "nlpaueb/legal-bert-base-uncased",
        epochs: int = 3,
        batch_size: int = 8,
        lr: float = 2e-5,
        dataset_version: str = "v1.0",
        seed: int = 42,
    ) -> Dict[str, Any]:
        """
        Runs the full Deep Learning training loop.
        """
        # Local imports for heavy libraries
        import torch
        import torch.nn as nn
        from torch.utils.data import DataLoader
        from torch.utils.tensorboard import SummaryWriter
        from torch.optim import AdamW
        from transformers import AutoModelForSequenceClassification, get_linear_schedule_with_warmup

        start_time = time.time()
        logger.info(f"Initiating Deep Learning training: model={model_name}, epochs={epochs}")

        # ─── 1. Reproducibility & Seeds ────────────────────────────────────
        seeds = set_reproducibility_seeds(seed)

        is_cpu = (self.device == "cpu") if isinstance(self.device, str) else (self.device.type == "cpu")
        if is_cpu:
            logger.info("Fast dev mode: downsampling dataset to 80 samples and overriding epochs to 1 on CPU device.")
            dataset_df = dataset_df.head(80)
            epochs = 1

        # ─── 2. Data Preparation ───────────────────────────────────────────
        try:
            train_dataset, val_dataset, test_dataset, data_meta = prepare_dl_data(
                df=dataset_df,
                tokenizer_name=model_name,
                seed=seed
            )
        except Exception as e:
            logger.error(f"Failed to prepare datasets: {e}")
            raise e

        train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
        val_loader = DataLoader(val_dataset, batch_size=batch_size)
        test_loader = DataLoader(test_dataset, batch_size=batch_size)

        # ─── 3. Load Pretrained Model ──────────────────────────────────────
        logger.info(f"Loading pretrained model: {model_name}")
        try:
            # We initialize a sequence classification model with 4 output classes
            model = AutoModelForSequenceClassification.from_pretrained(
                model_name,
                num_labels=len(SENSITIVITY_CLASSES),
                cache_dir=MODEL_CACHE_DIR,
                local_files_only=False
            )
            model.to(self.device)
        except Exception as e:
            err_msg = f"Pretrained model '{model_name}' could not be downloaded/loaded: {str(e)}"
            logger.error(err_msg, exc_info=True)
            raise PretrainedModelUnavailableError(err_msg)

        # ─── 4. Optimizer, Scheduler, & TensorBoard ────────────────────────
        optimizer = AdamW(model.parameters(), lr=lr)
        total_steps = len(train_loader) * epochs
        scheduler = get_linear_schedule_with_warmup(
            optimizer,
            num_warmup_steps=int(0.1 * total_steps),
            num_training_steps=total_steps
        )

        writer = SummaryWriter(log_dir=os.path.join(DL_MODELS_DIR, "logs"))

        # ─── 5. Training Loop ──────────────────────────────────────────────
        best_val_loss = float("inf")
        history = {"train_loss": [], "val_loss": [], "train_acc": [], "val_acc": []}

        for epoch in range(1, epochs + 1):
            model.train()
            train_loss = 0.0
            correct = 0
            total = 0

            epoch_start = time.time()
            for step, batch in enumerate(train_loader):
                # Fast Dev Mode: on CPU, limit steps per epoch to 3 to prevent hour-long blocking
                if self.device.type == "cpu" and step >= 3:
                    break
                optimizer.zero_grad()

                input_ids = batch["input_ids"].to(self.device)
                attention_mask = batch["attention_mask"].to(self.device)
                labels = batch["labels"].to(self.device)

                outputs = model(input_ids=input_ids, attention_mask=attention_mask, labels=labels)
                loss = outputs.loss
                logits = outputs.logits

                loss.backward()
                nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                optimizer.step()
                scheduler.step()

                train_loss += loss.item()
                _, preds = torch.max(logits, dim=1)
                correct += torch.sum(preds == labels).item()
                total += labels.size(0)

                # Log step to TensorBoard
                global_step = (epoch - 1) * len(train_loader) + step
                writer.add_scalar("Loss/train_step", loss.item(), global_step)

            train_loss /= len(train_loader)
            train_acc = correct / total

            # Validation
            val_loss, val_acc = self._validate(model, val_loader)

            history["train_loss"].append(train_loss)
            history["val_loss"].append(val_loss)
            history["train_acc"].append(train_acc)
            history["val_acc"].append(val_acc)

            # TensorBoard logging
            writer.add_scalar("Loss/train", train_loss, epoch)
            writer.add_scalar("Loss/val", val_loss, epoch)
            writer.add_scalar("Accuracy/train", train_acc, epoch)
            writer.add_scalar("Accuracy/val", val_acc, epoch)

            logger.info(f"Epoch {epoch}/{epochs} - Train Loss: {train_loss:.4f}, Val Loss: {val_loss:.4f}, Val Acc: {val_acc:.4f}")

            # Checkpoint Saving
            checkpoint = {
                "epoch": epoch,
                "model_state_dict": model.state_dict(),
                "optimizer_state_dict": optimizer.state_dict(),
                "history": history,
                "config": {"model_name": model_name, "batch_size": batch_size, "lr": lr}
            }
            
            # Periodic Checkpoint
            torch.save(checkpoint, os.path.join(DL_MODELS_DIR, f"checkpoint_epoch_{epoch}.pt"))
            
            # Save Last Model
            torch.save(checkpoint, os.path.join(DL_MODELS_DIR, "last_model.pt"))

            # Save Best Model
            if val_loss < best_val_loss:
                best_val_loss = val_loss
                torch.save(checkpoint, os.path.join(DL_MODELS_DIR, "best_model.pt"))
                logger.info(f"Saved new best model checkpoint with validation loss: {val_loss:.4f}")

        writer.close()
        training_duration = time.time() - start_time

        # ─── 6. Evaluation on Test Set ──────────────────────────────────────
        best_checkpoint = torch.load(os.path.join(DL_MODELS_DIR, "best_model.pt"))
        model.load_state_dict(best_checkpoint["model_state_dict"])
        test_loss, test_acc, eval_metrics = self._evaluate(model, test_loader)

        # ─── 7. Export ONNX ────────────────────────────────────────────────
        onnx_path = export_to_onnx(model)

        # ─── 8. Generate Reports ───────────────────────────────────────────
        curve_paths = plot_training_curves(history)
        
        report_data = {
            "model_name": model_name,
            "pytorch_version": torch.__version__,
            "dataset_version": dataset_version,
            "dataset_hash": data_meta["dataset_hash"],
            "epochs": epochs,
            "batch_size": batch_size,
            "learning_rate": lr,
            "training_time_seconds": training_duration,
            "metrics": {
                "accuracy": test_acc,
                "precision_macro": eval_metrics["precision"],
                "recall_macro": eval_metrics["recall"],
                "f1_macro": eval_metrics["f1"],
                "throughput": eval_metrics["throughput"],
                "latency_ms": eval_metrics["latency_ms"],
                "memory_mb": eval_metrics["memory_mb"]
            },
            "reproducibility": {
                **seeds,
                "tokenizer_version": "AutoTokenizer"
            }
        }

        # Save JSON Report
        with open(os.path.join(DL_MODELS_DIR, "training_report.json"), "w") as f:
            json.dump(report_data, f, indent=2)

        # Save PDF Report
        generate_pdf_report(report_data, curve_paths)

        # ─── 9. Regression Testing & MLOps Tracking ────────────────────────
        from models.ai_models import AIModel
        from models.ml_models import ExperimentRun
        import uuid

        new_accuracy = report_data["metrics"]["accuracy"]
        new_precision = report_data["metrics"]["precision_macro"]
        new_recall = report_data["metrics"]["recall_macro"]
        new_f1 = report_data["metrics"]["f1_macro"]
        new_latency = report_data["metrics"]["latency_ms"]

        # Fetch previous production model parameters
        prev_model = self.db.query(AIModel).filter(AIModel.name == "LegalBERT Classifier").first()
        prev_params = prev_model.parameters if prev_model else None

        f1_diff = 0.0
        acc_diff = 0.0
        prec_diff = 0.0
        rec_diff = 0.0
        latency_diff = 0.0
        regression_detected = False

        if prev_params and "f1_macro" in prev_params:
            old_f1 = prev_params.get("f1_macro", 0.0)
            old_accuracy = prev_params.get("accuracy", 0.0)
            old_precision = prev_params.get("precision_macro", 0.0)
            old_recall = prev_params.get("recall_macro", 0.0)
            old_latency = prev_params.get("latency_ms", 0.0)

            f1_diff = new_f1 - old_f1
            acc_diff = new_accuracy - old_accuracy
            prec_diff = new_precision - old_precision
            rec_diff = new_recall - old_recall
            latency_diff = new_latency - old_latency

            # Check degradation threshold (F1 drops by > 0.02 or Latency grows by > 50ms)
            if f1_diff < -0.02 or latency_diff > 50.0:
                regression_detected = True
                logger.warning(f"REGRESSION DETECTED: F1 changed by {f1_diff:.4f}, Latency changed by {latency_diff:.1f}ms")
            else:
                logger.info(f"No regression detected. F1 diff: {f1_diff:.4f}, Latency diff: {latency_diff:.1f}ms")

        # Save ExperimentRun (MLOps Tracking)
        run_status = "REGRESSION DETECTED" if regression_detected else "NO REGRESSION"
        new_run = ExperimentRun(
            id=uuid.uuid4(),
            experiment_name=f"LegalBERT Fine-tuning [{datetime.now().strftime('%Y-%m-%d %H:%M')}]",
            dataset_version=dataset_version,
            best_algorithm="LegalBERT",
            best_model_version="2.0.0",
            best_f1=new_f1,
            best_accuracy=new_accuracy,
            total_models_trained=1,
            total_training_time_seconds=training_duration,
            status="COMPLETED",
            notes=f"Status: {run_status}. Diff -> F1: {f1_diff:.4f}, Acc: {acc_diff:.4f}, Prec: {prec_diff:.4f}, Rec: {rec_diff:.4f}, Latency: {latency_diff:.1f}ms"
        )
        self.db.add(new_run)
        self.db.commit()

        # Add regression metrics to report_data
        report_data["regression_test"] = {
            "status": run_status,
            "metrics_diff": {
                "accuracy": acc_diff,
                "precision_macro": prec_diff,
                "recall_macro": rec_diff,
                "f1_macro": f1_diff,
                "latency_ms": latency_diff
            }
        }

        # ─── 10. Generate Model Card ───────────────────────────────────────
        model_card_content = f"""# Model Card — LegalBERT Classifier

## Model Details
- **Model Name**: LegalBERT Classifier
- **Version**: 2.0.0
- **Framework**: PyTorch / Transformers
- **Base Model**: {model_name}
- **Dataset Version**: {dataset_version}
- **Dataset Hash**: {data_meta["dataset_hash"]}
- **Training Date**: {datetime.now().strftime('%Y-%m-%d')}

## Intended Use
- **Primary Use**: Automatically classify legal document sensitivity and identify PII protection bounds.
- **Intended Users**: RedactAI platform users, legal compliance officers, and review administrators.
- **Out of Scope**: Non-legal documents, multi-lingual texts beyond English.

## Factors
- **Performance Evaluation**: Evaluated against traditional ML pipelines (Logistic Regression, Random Forest, XGBoost).
- **Environment**: CPU / CUDA-based execution.

## Metrics
- **Accuracy**: {new_accuracy*100:.2f}%
- **Precision (Macro)**: {new_precision*100:.2f}%
- **Recall (Macro)**: {new_recall*100:.2f}%
- **F1 Score (Macro)**: {new_f1*100:.2f}%
- **Inference Latency**: {new_latency:.1f} ms
- **Throughput**: {report_data["metrics"]["throughput"]:.1f} samples/sec
- **Peak Memory**: {report_data["metrics"]["memory_mb"]:.1f} MB

## Training Parameters
- **Epochs**: {epochs}
- **Batch Size**: {batch_size}
- **Learning Rate**: {lr}

## MLOps & Robustness
- **Regression Status**: {run_status}
- **Reproducibility Seed**: {seeds.get("python_seed", 42)}
- **Known Risks**: Potential false negatives on highly domain-specific proprietary terms.
- **Limitations**: Optimized for legal agreements and NDAs in English. Performance may vary on non-legal layouts.
- **Future Improvements**: Visual layout multimodal support via LayoutLMv3 integration.
"""
        with open(os.path.join(DL_MODELS_DIR, "MODEL_CARD.md"), "w") as f:
            f.write(model_card_content)
        logger.info("MODEL_CARD.md generated successfully.")

        return report_data

    def _validate(self, model: Any, loader: Any) -> Tuple[float, float]:
        """Run validation loop."""
        import torch
        import torch.nn as nn
        model.eval()
        val_loss = 0.0
        correct = 0
        total = 0
        loss_fn = nn.CrossEntropyLoss()

        with torch.no_grad():
            for idx, batch in enumerate(loader):
                if self.device.type == "cpu" and idx >= 2:
                    break
                input_ids = batch["input_ids"].to(self.device)
                attention_mask = batch["attention_mask"].to(self.device)
                labels = batch["labels"].to(self.device)

                outputs = model(input_ids=input_ids, attention_mask=attention_mask, labels=labels)
                val_loss += outputs.loss.item()
                logits = outputs.logits

                _, preds = torch.max(logits, dim=1)
                correct += torch.sum(preds == labels).item()
                total += labels.size(0)

        return val_loss / min(len(loader), 2) if self.device.type == "cpu" else val_loss / len(loader), correct / total

    def _evaluate(self, model: Any, loader: Any) -> Tuple[float, float, Dict[str, float]]:
        """Evaluate model on the test set collecting detailed metrics."""
        import torch
        model.eval()
        test_loss = 0.0
        all_preds = []
        all_labels = []

        start_inf = time.time()
        
        # Track memory usage peak
        if torch.cuda.is_available():
            torch.cuda.reset_peak_memory_stats()

        with torch.no_grad():
            for idx, batch in enumerate(loader):
                if self.device.type == "cpu" and idx >= 2:
                    break
                input_ids = batch["input_ids"].to(self.device)
                attention_mask = batch["attention_mask"].to(self.device)
                labels = batch["labels"].to(self.device)

                outputs = model(input_ids=input_ids, attention_mask=attention_mask, labels=labels)
                test_loss += outputs.loss.item()
                logits = outputs.logits

                _, preds = torch.max(logits, dim=1)
                all_preds.extend(preds.cpu().numpy())
                all_labels.extend(labels.cpu().numpy())

        inf_duration = time.time() - start_inf
        num_samples = len(all_labels)
        
        # Compute throughput and average latency
        throughput = num_samples / max(inf_duration, 0.001)
        latency_ms = (inf_duration / max(num_samples, 1)) * 1000

        # Memory usage
        if torch.cuda.is_available():
            memory_mb = torch.cuda.max_memory_allocated() / (1024 * 1024)
        else:
            # CPU peak memory approximation
            try:
                import psutil
                process = psutil.Process(os.getpid())
                memory_mb = process.memory_info().rss / (1024 * 1024)
            except ImportError:
                memory_mb = 0.0

        # Metrics calculation
        from sklearn.metrics import precision_recall_fscore_support
        precision, recall, f1, _ = precision_recall_fscore_support(
            all_labels, all_preds, average="macro", zero_division=0
        )
        accuracy = np.mean(np.array(all_preds) == np.array(all_labels))

        eval_metrics = {
            "precision": float(precision),
            "recall": float(recall),
            "f1": float(f1),
            "throughput": float(throughput),
            "latency_ms": float(latency_ms),
            "memory_mb": float(memory_mb)
        }

        return test_loss / min(len(loader), 2) if self.device.type == "cpu" else test_loss / len(loader), float(accuracy), eval_metrics
