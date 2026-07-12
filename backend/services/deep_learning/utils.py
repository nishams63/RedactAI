"""
Utilities — Level 2 Deep Learning Enhancement
Implements ONNX exporting, plotting (curves, matrices),
and automated PDF/JSON training reports generation.
"""
import os
import json
import logging
from typing import Dict, Any, List

import numpy as np
import torch
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.pyplot as plt

# Try importing ONNX dependencies
try:
    import onnx
    import onnxruntime as ort
    ONNX_AVAILABLE = True
except ImportError:
    ONNX_AVAILABLE = False

# Try importing ReportLab for PDF generation
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

logger = logging.getLogger("redactai.dl.utils")

DL_MODELS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "dl_models"
)
os.makedirs(DL_MODELS_DIR, exist_ok=True)


def export_to_onnx(model: torch.nn.Module, max_length: int = 512) -> str:
    """Export PyTorch transformer model to ONNX for fast inference."""
    if not ONNX_AVAILABLE:
        logger.warning("ONNX or onnxruntime packages missing. Skipping ONNX export.")
        return ""

    onnx_path = os.path.join(DL_MODELS_DIR, "model.onnx")
    logger.info(f"Exporting PyTorch model to ONNX: {onnx_path}")

    # Set model to evaluation mode
    model.eval()

    # Create dummy inputs matching token shape (batch_size=1, max_length)
    dummy_input_ids = torch.zeros((1, max_length), dtype=torch.long)
    dummy_attention_mask = torch.ones((1, max_length), dtype=torch.long)

    try:
        torch.onnx.export(
            model,
            (dummy_input_ids, dummy_attention_mask),
            onnx_path,
            input_names=["input_ids", "attention_mask"],
            output_names=["output"],
            dynamic_axes={
                "input_ids": {0: "batch_size", 1: "sequence_length"},
                "attention_mask": {0: "batch_size", 1: "sequence_length"},
                "output": {0: "batch_size"},
            },
            opset_version=14,
        )
        logger.info("ONNX export completed successfully.")
        return onnx_path
    except Exception as e:
        logger.error(f"Failed to export to ONNX: {e}", exc_info=True)
        return ""


def plot_training_curves(history: Dict[str, List[float]]) -> Dict[str, str]:
    """Generate and save matplotlib training graphs."""
    plots = {}
    epochs = range(1, len(history["train_loss"]) + 1)

    # 1. Loss Curve
    plt.figure()
    plt.plot(epochs, history["train_loss"], label="Train Loss", marker="o")
    plt.plot(epochs, history["val_loss"], label="Val Loss", marker="s")
    plt.title("Training & Validation Loss")
    plt.xlabel("Epoch")
    plt.ylabel("Loss")
    plt.legend()
    plt.grid(True)
    loss_path = os.path.join(DL_MODELS_DIR, "loss_curve.png")
    plt.savefig(loss_path, dpi=300)
    plt.close()
    plots["loss_curve"] = loss_path

    # 2. Accuracy Curve
    if "train_acc" in history and "val_acc" in history:
        plt.figure()
        plt.plot(epochs, history["train_acc"], label="Train Acc", marker="o", color="emerald" if "emerald" in matplotlib.colors.cnames else "green")
        plt.plot(epochs, history["val_acc"], label="Val Acc", marker="s", color="orange")
        plt.title("Training & Validation Accuracy")
        plt.xlabel("Epoch")
        plt.ylabel("Accuracy")
        plt.legend()
        plt.grid(True)
        acc_path = os.path.join(DL_MODELS_DIR, "accuracy_curve.png")
        plt.savefig(acc_path, dpi=300)
        plt.close()
        plots["accuracy_curve"] = acc_path

    return plots


def generate_pdf_report(
    report_data: Dict[str, Any],
    curve_paths: Dict[str, str]
) -> str:
    """Generate a formal PDF evaluation and training report."""
    if not REPORTLAB_AVAILABLE:
        logger.warning("reportlab is not installed. Skipping PDF report generation.")
        return ""

    pdf_path = os.path.join(DL_MODELS_DIR, "training_report.pdf")
    logger.info(f"Generating PDF report: {pdf_path}")

    try:
        doc = SimpleDocTemplate(
            pdf_path,
            pagesize=letter,
            rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40
        )
        
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'TitleStyle',
            parent=styles['Heading1'],
            fontSize=22,
            textColor=colors.HexColor("#3F51B5"),
            spaceAfter=15
        )
        subtitle_style = ParagraphStyle(
            'SubTitleStyle',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor("#1A237E"),
            spaceBefore=10,
            spaceAfter=5
        )
        normal_style = styles['Normal']
        
        story = []

        # Title
        story.append(Paragraph("RedactAI — Deep Learning Training Report", title_style))
        story.append(Spacer(1, 10))

        # Model details table
        details = [
            ["Parameter", "Value"],
            ["Model Name", report_data.get("model_name", "LegalBERT")],
            ["Framework", "PyTorch / Transformers"],
            ["Pytorch Version", report_data.get("pytorch_version", "")],
            ["Dataset Version", report_data.get("dataset_version", "")],
            ["Total Epochs", str(report_data.get("epochs", ""))],
            ["Batch Size", str(report_data.get("batch_size", ""))],
            ["Learning Rate", str(report_data.get("learning_rate", ""))],
            ["Training Time (sec)", f"{report_data.get('training_time_seconds', 0.0):.2f}"],
        ]
        t = Table(details, colWidths=[200, 300])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#E8EAF6")),
            ('TEXTCOLOR', (0,0), (-1,0), colors.HexColor("#1A237E")),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ('GRID', (0,0), (-1,-1), 1, colors.HexColor("#C5CAE9")),
        ]))
        story.append(t)
        story.append(Spacer(1, 15))

        # Metrics
        story.append(Paragraph("Evaluation Metrics", subtitle_style))
        metrics_data = [
            ["Metric", "Value"],
            ["Accuracy", f"{report_data.get('metrics', {}).get('accuracy', 0.0)*100:.2f}%"],
            ["Precision (Macro)", f"{report_data.get('metrics', {}).get('precision_macro', 0.0)*100:.2f}%"],
            ["Recall (Macro)", f"{report_data.get('metrics', {}).get('recall_macro', 0.0)*100:.2f}%"],
            ["F1 Score (Macro)", f"{report_data.get('metrics', {}).get('f1_macro', 0.0)*100:.2f}%"],
            ["Throughput (samples/s)", f"{report_data.get('metrics', {}).get('throughput', 0.0):.2f}"],
            ["Avg Latency (ms)", f"{report_data.get('metrics', {}).get('latency_ms', 0.0):.2f}"],
            ["Memory Peak (MB)", f"{report_data.get('metrics', {}).get('memory_mb', 0.0):.2f}"],
        ]
        t_metrics = Table(metrics_data, colWidths=[200, 300])
        t_metrics.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#E8EAF6")),
            ('TEXTCOLOR', (0,0), (-1,0), colors.HexColor("#1A237E")),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ('GRID', (0,0), (-1,-1), 1, colors.HexColor("#C5CAE9")),
        ]))
        story.append(t_metrics)
        story.append(Spacer(1, 20))

        # Add training curve image
        if "loss_curve" in curve_paths and os.path.exists(curve_paths["loss_curve"]):
            story.append(Paragraph("Training Loss Curve", subtitle_style))
            story.append(Image(curve_paths["loss_curve"], width=300, height=200))

        doc.build(story)
        logger.info("PDF report compiled successfully.")
        return pdf_path
    except Exception as e:
        logger.error(f"Failed to generate PDF report: {e}", exc_info=True)
        return ""
