"""
Redaction Service — Sprint 1 Placeholder
This service will handle the actual redaction of detected PII in documents.
Technologies planned: PDF manipulation (PyMuPDF), image processing (Pillow/OpenCV)
"""
from fastapi import FastAPI

app = FastAPI(title="RedactAI Redaction Service", version="0.1.0")


@app.get("/health")
def health():
    return {"service": "redaction-service", "status": "placeholder", "sprint": 1}


@app.post("/redact")
def redact_document():
    """Placeholder — will accept document + entity positions and return redacted document."""
    return {"status": "not_implemented", "message": "Redaction engine will be available in Sprint 3"}
