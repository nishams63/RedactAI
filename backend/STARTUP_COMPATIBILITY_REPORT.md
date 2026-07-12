# Startup Compatibility Report

- **Deployment Profile**: production
- **Deployment Grade**: E

## Subsystems Status
- **OCR Subsystem**: ACTIVE
- **Sensitivity / PII Subsystem**: ACTIVE
- **Legal AI / RAG Subsystem**: ACTIVE

## Feature Classifications

### Working Features
- SQLite database initializer
- Deployment Profile: production
- Local filesystem storage driver

### Fallback Features
- PII / Sensitivity Classification (Rule-based fallback active)
- Deep Learning (Rule-based fallback active)
- OCR Pipeline (PyMuPDF / PyPDF text parser fallback active)
- Legal AI Q&A and RAG Semantic Embeddings (Rule-based fallback active)

### Disabled Features
- PII / Sensitivity Classification (XGBoost ML model)
- Deep Learning (LegalBERT/LayoutLM neural inference)
- OCR Pipeline (EasyOCR/PaddleOCR neural engines)
- Legal AI Q&A and RAG Semantic Embeddings (Transformers/Torch neural model)

## Dependency Manifest

```json
{
    "deployment_profile": "production",
    "grade": "E",
    "dependencies": {
        "torch": {
            "installed": false,
            "version": null,
            "availability": "Unavailable",
            "fallback_available": true
        },
        "transformers": {
            "installed": false,
            "version": null,
            "availability": "Unavailable",
            "fallback_available": true
        },
        "sentence_transformers": {
            "installed": false,
            "version": null,
            "availability": "Unavailable",
            "fallback_available": true
        },
        "onnxruntime": {
            "installed": false,
            "version": null,
            "availability": "Unavailable",
            "fallback_available": true
        },
        "xgboost": {
            "installed": false,
            "version": null,
            "availability": "Unavailable",
            "fallback_available": true
        },
        "spacy": {
            "installed": false,
            "version": null,
            "availability": "Unavailable",
            "fallback_available": true
        },
        "easyocr": {
            "installed": false,
            "version": null,
            "availability": "Unavailable",
            "fallback_available": true
        },
        "paddleocr": {
            "installed": false,
            "version": null,
            "availability": "Unavailable",
            "fallback_available": true
        },
        "reportlab": {
            "installed": false,
            "version": null,
            "availability": "Unavailable",
            "fallback_available": true
        }
    }
}
```
