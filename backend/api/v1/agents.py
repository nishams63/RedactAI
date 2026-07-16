import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional

from dependencies import get_db, get_current_user
from models.user import User
from models.agent_registry import AgentRegistryModel, AgentMetricsLog
from services.legal_ai.orchestrator_v2 import AgentOrchestratorV2
from services.legal_ai.agents.registry import AgentRegistry

router = APIRouter(prefix="/agents", tags=["Multi-Agent Platform"])

@router.post("/execute")
def execute_agent_workflow(
    payload: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Executes the multi-agent task planner and workflow generator synchronously."""
    query = payload.get("query")
    doc_ids = payload.get("document_ids", [])
    
    if not query:
        raise HTTPException(status_code=400, detail="query string is required")
        
    orchestrator = AgentOrchestratorV2(db)
    
    res_list = list(orchestrator.execute_workflow(
        query=query,
        current_user=current_user,
        document_ids=doc_ids
    ))
    
    completion = next((e for e in res_list if e.get("event") == "workflow_completed"), None)
    if not completion:
        raise HTTPException(status_code=500, detail="Workflow did not complete successfully.")
        
    return completion["data"]


@router.get("/registry")
def get_agent_registry(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Returns list of registered agents and their active capabilities."""
    # Instantiating the orchestrator triggers default agents self-registration
    AgentOrchestratorV2(db)
    agents = db.query(AgentRegistryModel).all()
    return [
        {
            "id": str(a.id),
            "agent_id": a.agent_id,
            "name": a.name,
            "description": a.description,
            "version": a.version,
            "is_active": a.is_active,
            "capabilities": a.capabilities,
            "supported_tasks": a.supported_tasks,
            "policy": a.policy,
            "health_status": a.health_status
        }
        for a in agents
    ]


@router.post("/registry/toggle")
def toggle_agent_activation(
    payload: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Activates or deactivates an agent definition version."""
    agent_id = payload.get("agent_id")
    version = payload.get("version")
    is_active = payload.get("is_active", True)
    
    if not agent_id or not version:
        raise HTTPException(status_code=400, detail="agent_id and version are required")
        
    registry = AgentRegistry(db)
    updated = registry.toggle_agent_active(agent_id, version, is_active)
    
    if not updated:
        raise HTTPException(status_code=404, detail="Agent version not found in registry")
        
    return {
        "agent_id": updated.agent_id,
        "version": updated.version,
        "is_active": updated.is_active
    }


@router.get("/metrics")
def get_agent_health_metrics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieves execution metrics and average latencies for all registered agent tags."""
    AgentOrchestratorV2(db)
    metrics = db.query(AgentMetricsLog).all()
    return [
        {
            "agent_id": m.agent_id,
            "version": m.version,
            "success_count": m.success_count,
            "failure_count": m.failure_count,
            "total_latency_ms": m.total_latency_ms,
            "avg_latency_ms": round(m.total_latency_ms / max(1, m.success_count + m.failure_count), 2),
            "last_failure_at": m.last_failure_at.isoformat() if m.last_failure_at else None,
            "last_success_at": m.last_success_at.isoformat() if m.last_success_at else None,
            "cpu_usage_pct": m.cpu_usage_pct,
            "memory_usage_mb": m.memory_usage_mb
        }
        for m in metrics
    ]
