"""
NER Service — Sprint 1 Placeholder
This service will handle Named Entity Recognition for legal documents.
Technologies planned: spaCy, Hugging Face Transformers, custom legal NER models
"""
from fastapi import FastAPI

app = FastAPI(title="RedactAI NER Service", version="0.1.0")


@app.get("/health")
def health():
    return {"service": "ner-service", "status": "placeholder", "sprint": 1}


@app.post("/extract")
def extract_entities():
    """Placeholder — will accept text and return recognized entities with positions."""
    return {"status": "not_implemented", "message": "NER extraction will be available in Sprint 2"}
