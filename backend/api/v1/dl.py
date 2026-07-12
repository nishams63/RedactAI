"""Deep Learning API Router — Level 2 Deep Learning Enhancement."""
import os
import json
from typing import List
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
import pandas as pd

from dependencies import get_db, check_permissions, get_current_user
from models.user import User
from models.ai_models import AIModel
from models.ml_models import TrainingDataset
from models.document_intelligence import DocumentMetadata, DocumentPage
from schemas.dl import (
    DLTrainRequest, DLTrainResponse, DLComparisonResponse, DLInferenceResponse
)
# Deep Learning imports deferred to lazy handlers to prevent startup dependency side-effects
from services.ml.dataset_generator import DatasetGenerator

router = APIRouter(prefix="/dl", tags=["Deep Learning"])


@router.post("/train", response_model=DLTrainResponse)
def train_deep_learning(
    request: DLTrainRequest,
    current_user: User = Depends(check_permissions(["Admin"])),
    db: Session = Depends(get_db),
):
    """
    Triggers the Level 2 Deep Learning training loop.
    1. Loads the latest hybrid dataset (or generates one of the requested size).
    2. Fine-tunes LegalBERT on the dataset.
    3. Saves training metrics, loss curves, and generates PDF/JSON reports.
    4. Exports model to ONNX format.
    """
    # Find latest training dataset or generate a new one
    dataset_record = db.query(TrainingDataset).order_by(TrainingDataset.created_at.desc()).first()
    if not dataset_record or dataset_record.total_samples != request.dataset_size:
        # Generate new dataset to match the size requested
        generator = DatasetGenerator(db)
        meta = generator.generate(total_size=request.dataset_size)
        csv_path = meta["file_path"]
        dataset_version = meta["dataset_version"]
    else:
        csv_path = dataset_record.file_path
        dataset_version = dataset_record.dataset_version

    if not os.path.exists(csv_path):
        raise HTTPException(status_code=404, detail=f"Dataset file not found at {csv_path}")

    # Read dataset
    df = pd.read_csv(csv_path)

    from services.deep_learning.trainer import DLTrainer, PretrainedModelUnavailableError
    trainer = DLTrainer(db)
    try:
        report = trainer.train(
            dataset_df=df,
            epochs=request.epochs,
            batch_size=request.batch_size,
            lr=request.learning_rate,
            dataset_version=dataset_version
        )
        
        # Save model details into legacy AIModel registry
        dl_model = db.query(AIModel).filter(AIModel.name == "LegalBERT Classifier").first()
        if not dl_model:
            dl_model = AIModel(name="LegalBERT Classifier", type="REDACTION")  # Swappable type
            db.add(dl_model)
        
        dl_model.version = "2.0.0"
        dl_model.status = "ACTIVE"
        dl_model.parameters = {
            "framework": "PyTorch",
            "model_name": "nlpaueb/legal-bert-base-uncased",
            "dataset_version": dataset_version,
            "epochs": request.epochs,
            "batch_size": request.batch_size,
            "learning_rate": request.learning_rate,
            "accuracy": report["metrics"]["accuracy"],
            "f1_macro": report["metrics"]["f1_macro"],
            "reproducibility": report["reproducibility"]
        }
        db.commit()

        return report

    except PretrainedModelUnavailableError as err:
        # Report the exact state if the pretrained model cannot be downloaded
        raise HTTPException(
            status_code=503,
            detail=f"Pretrained Model Unavailable: {str(err)}. Double check your network connection or internet availability."
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Deep Learning training failed: {str(e)}")


@router.post("/predict/{document_id}", response_model=DLInferenceResponse)
def predict_dl_sensitivity(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Performs consensus sensitivity prediction on a document using ML + DL pipelines.
    Resolves winning confidence and agreement audits.
    """
    # Fetch document text from DB
    pages = db.query(DocumentPage).filter(DocumentPage.document_id == document_id).order_by(DocumentPage.page_number.asc()).all()
    text = " ".join(p.text for p in pages) if pages else ""
    
    from services.deep_learning.inference import DLInferenceEngine
    engine = DLInferenceEngine(db)
    try:
        result = engine.predict_consensus(document_id, text)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Consensus prediction failed: {str(e)}")


@router.get("/models")
def list_dl_models(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lists registered Deep Learning models."""
    models = db.query(AIModel).filter(AIModel.name.like("%BERT%")).all()
    return models


@router.get("/evaluation")
def get_dl_evaluation(
    current_user: User = Depends(get_current_user),
):
    """Returns training loss, accuracy, and generated report links."""
    from services.deep_learning.utils import DL_MODELS_DIR
    report_path = os.path.join(DL_MODELS_DIR, "training_report.json")
    if not os.path.exists(report_path):
        raise HTTPException(status_code=404, detail="DL training report not found. Train model first.")

    with open(report_path, "r") as f:
        data = json.load(f)
    return data


@router.get("/comparison", response_model=DLComparisonResponse)
def get_ml_dl_comparison(
    current_user: User = Depends(get_current_user),
):
    """Returns unified latency, throughput, memory, and accuracy comparison table."""
    try:
        from services.deep_learning.evaluator import DLEvaluator
        comparison = DLEvaluator.get_comparison()
        return comparison
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to compile comparison: {str(e)}")


@router.get("/validation-report")
def get_validation_report(
    current_user: User = Depends(get_current_user),
):
    """Returns the latest generated validation report."""
    from services.deep_learning.utils import DL_MODELS_DIR
    report_path = os.path.join(DL_MODELS_DIR, "validation_report.json")
    if not os.path.exists(report_path):
        # Try root backup
        report_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "Validation_Report.json")
        if not os.path.exists(report_path):
            raise HTTPException(status_code=404, detail="Validation report not found. Run validation script first.")

    with open(report_path, "r") as f:
        data = json.load(f)
    return data


@router.get("/validation-pdf")
def get_validation_pdf(
    current_user: User = Depends(get_current_user),
):
    """Downloads the compiled PDF Validation Report."""
    from fastapi.responses import FileResponse
    pdf_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "Validation_Report.pdf")
    if not os.path.exists(pdf_path):
        # Fallback to model dir
        from services.deep_learning.utils import DL_MODELS_DIR
        pdf_path = os.path.join(DL_MODELS_DIR, "Validation_Report.pdf")
        if not os.path.exists(pdf_path):
            raise HTTPException(status_code=404, detail="Validation PDF report not found. Run validation script first.")

    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename="Validation_Report.pdf"
    )


@router.get("/curves/{filename}")
def get_training_curve(filename: str):
    """Serve generated training curve images."""
    from fastapi.responses import FileResponse
    from services.deep_learning.utils import DL_MODELS_DIR
    path = os.path.join(DL_MODELS_DIR, filename)
    if not os.path.exists(path) or filename not in ["loss_curve.png", "accuracy_curve.png"]:
        raise HTTPException(status_code=404, detail="Curve image not found")
    return FileResponse(path)
