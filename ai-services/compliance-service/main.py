"""
Compliance Service — Sprint 1 Placeholder
This service will handle compliance rule checking against Indian data protection laws.
Technologies planned: Rule engine, DPDP Act compliance checks, GDPR mapping
"""
from fastapi import FastAPI

app = FastAPI(title="RedactAI Compliance Service", version="0.1.0")


@app.get("/health")
def health():
    return {"service": "compliance-service", "status": "placeholder", "sprint": 1}


@app.post("/check")
def check_compliance():
    """Placeholder — will accept document metadata and return compliance assessment."""
    return {"status": "not_implemented", "message": "Compliance checking will be available in Sprint 3"}
