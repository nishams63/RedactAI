"""
Agent Service — Sprint 1 Placeholder
This service will orchestrate agentic AI workflows for document processing.
Technologies planned: LangGraph, LangChain, multi-agent orchestration
"""
from fastapi import FastAPI

app = FastAPI(title="RedactAI Agent Service", version="0.1.0")


@app.get("/health")
def health():
    return {"service": "agent-service", "status": "placeholder", "sprint": 1}


@app.post("/orchestrate")
def orchestrate_pipeline():
    """Placeholder — will accept processing request and orchestrate multi-step AI pipeline."""
    return {"status": "not_implemented", "message": "Agentic AI orchestration will be available in Sprint 5"}
