import uuid
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from models.ml_models import DLExperiment

class DLExperimentTracker:
    """
    MLOps-grade experiment tracking utility to persist Deep Learning training logs in PostgreSQL/SQLite.
    """
    def __init__(self, db: Session):
        self.db = db

    def start_run(self, model_name: str, dataset_version: str = "v1.0") -> str:
        """Starts a new experiment run and registers it in the DB in RUNNING status."""
        run_id = str(uuid.uuid4())
        experiment = DLExperiment(
            experiment_id=run_id,
            model_name=model_name,
            dataset_version=dataset_version,
            loss=0.0,
            accuracy=0.0,
            precision=0.0,
            recall=0.0,
            f1=0.0,
            training_time=0.0,
            hardware="Unknown"
        )
        self.db.add(experiment)
        self.db.commit()
        return run_id

    def log_metrics(self, run_id: str, metrics: Dict[str, Any]) -> None:
        """Updates metrics and training results for an active run."""
        run = self.db.query(DLExperiment).filter(DLExperiment.experiment_id == run_id).first()
        if not run:
            return
            
        run.loss = float(metrics.get("loss", run.loss))
        run.accuracy = float(metrics.get("accuracy", run.accuracy))
        run.precision = float(metrics.get("precision", run.precision))
        run.recall = float(metrics.get("recall", run.recall))
        run.f1 = float(metrics.get("f1_macro", run.f1))
        
        run.learning_rate = float(metrics.get("learning_rate", run.learning_rate or 0.0))
        run.batch_size = int(metrics.get("batch_size", run.batch_size or 0))
        run.epochs = int(metrics.get("epochs", run.epochs or 0))
        run.optimizer = str(metrics.get("optimizer", run.optimizer or ""))
        run.training_time = float(metrics.get("training_time", run.training_time or 0.0))
        run.hardware = str(metrics.get("hardware", run.hardware or "CPU"))
        run.random_seed = int(metrics.get("random_seed", run.random_seed or 42))
        run.checkpoint_path = str(metrics.get("checkpoint_path", run.checkpoint_path or ""))
        run.onnx_export = bool(metrics.get("onnx_export", run.onnx_export))
        
        self.db.commit()

    def get_experiments(self) -> List[DLExperiment]:
        """Lists all registered Deep Learning experiments."""
        return self.db.query(DLExperiment).order_by(DLExperiment.created_at.desc()).all()

    def compare_runs(self, run_ids: List[str]) -> List[DLExperiment]:
        """Compares multiple specific experiment runs side by side."""
        return self.db.query(DLExperiment).filter(DLExperiment.experiment_id.in_(run_ids)).all()
