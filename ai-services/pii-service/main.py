"""
PII Detection Service — Sprint 1 Placeholder
This service will handle PII (Personally Identifiable Information) detection.
Technologies planned: spaCy, custom NER models, regex patterns for Indian PII (Aadhaar, PAN, etc.)
"""
from fastapi import FastAPI

app = FastAPI(title="RedactAI PII Service", version="0.1.0")


@app.get("/health")
def health():
    return {"service": "pii-service", "status": "placeholder", "sprint": 1}


@app.post("/detect")
def detect_pii():
    """Placeholder — will accept text content and return detected PII entities."""
    return {"status": "not_implemented", "message": "PII detection will be available in Sprint 2"}
