# RedactAI Git Repository & Model Guide

This guide details repository hygiene standards, gitignore exclusions, model management, and setup guidelines for developers and contributors.

## 1. Tracked vs Ignored Assets

### What is Tracked:
*   **Application Source Code**: Backend API routers (`FastAPI`), database models, business logic services, and frontend portal React components (`Next.js 15`).
*   **Database Migrations**: Alembic configuration files and version history scripts (`backend/alembic/`).
*   **Validation Checklists**: Enterprise code validators, and E2E test runner suites (`backend/scripts/`).
*   **Deployment Templates**: Root `docker-compose.yml`, Dockerfiles, and safe environment templates (`.env.example`).

### What is Ignored:
*   **Large Model Weights**: ONNX networks, PyTorch checkpoints, and weights files (`*.onnx`, `*.onnx.data`, `*.pth`, `*.pt`, `*.ckpt`, `*.safetensors`, `dl_models/`).
*   **System Environment Credentials**: Specific configuration environment settings (`.env`, `.env.*`).
*   **Runtime Cache & Preview Uploads**: Upload documents, ocr cache logs, and vector database indices (`local_storage/`, `uploads/`, `model_cache/`).
*   **Generated PDF Cards**: Output security audits, quality runs, and performance timing reviews (`Final_Security_Report.pdf`, etc.).

---

## 2. Why Model Weights are Excluded
ML/DL model files are extremely large (e.g. `model.onnx.data` is 417.67 MB), exceed Git's standard 100MB single-file size threshold, and can result in server reject flags during pushes. Committing these binary weights directly into Git history pollutes repository download sizes and slows down pull requests. 

Instead, model weights must be retrieved programmatically from public model registries (like HuggingFace Hub) or trained locally.

---

## 3. How to Regenerate or Download Models

### HuggingFace Transformers (SLM QA):
The platform dynamically downloads and caches tokenizer and weights files for the QA engine (`Qwen/Qwen2.5-0.5B-Instruct`) during startup validation.
No manual download is required, provided the backend uvicorn gateway has internet access during the first start.

### Custom Deep Learning (Layout Classification):
To train and compile the layout classification models locally:
1. Navigate to deep learning services directory:
   ```bash
   cd backend/services/deep_learning
   ```
2. Execute the model trainer to generate checkpoints:
   ```bash
   python trainer.py
   ```
3. Export the trained PyTorch network to the ONNX serialization format for low-latency inference runtime:
   ```bash
   python exporter.py
   ```
   *Note: Ensure the resulting `.onnx` and `.onnx.data` files are saved to `backend/dl_models/` (which is safely excluded from Git).*
