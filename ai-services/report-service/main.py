"""
Report Service — Sprint 1 Placeholder
This service will generate compliance and redaction reports.
Technologies planned: ReportLab, Jinja2 templates, PDF generation
"""
from fastapi import FastAPI

app = FastAPI(title="RedactAI Report Service", version="0.1.0")


@app.get("/health")
def health():
    return {"service": "report-service", "status": "placeholder", "sprint": 1}


@app.post("/generate")
def generate_report():
    """Placeholder — will accept document/compliance data and return a generated report."""
    return {"status": "not_implemented", "message": "Report generation will be available in Sprint 4"}
