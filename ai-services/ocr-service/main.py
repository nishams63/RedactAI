"""
OCR Service — Sprint 1 Placeholder
This service will handle Optical Character Recognition in future sprints.
Technologies planned: Tesseract, LayoutLM, PaddleOCR
"""
from fastapi import FastAPI

app = FastAPI(title="RedactAI OCR Service", version="0.1.0")


@app.get("/health")
def health():
    return {"service": "ocr-service", "status": "placeholder", "sprint": 1}


@app.post("/process")
def process_document():
    """Placeholder — will accept document binary and return extracted text."""
    return {"status": "not_implemented", "message": "OCR processing will be available in Sprint 2"}
