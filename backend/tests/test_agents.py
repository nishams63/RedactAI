import uuid
import pytest
from sqlalchemy.orm import Session
from database.session import SessionLocal, Base, engine

# Force all database tables to exist before tests execute
Base.metadata.create_all(bind=engine)

from models.user import User
from models.organization import Organization
from models.agent_registry import AgentRegistryModel, AgentMetricsLog
from services.legal_ai.orchestrator_v2 import AgentOrchestratorV2
from services.legal_ai.agents.registry import AgentRegistry
from services.legal_ai.agents.planner import AgentPlanner
from services.legal_ai.agents.context import SharedContext
from services.legal_ai.agents.workflow import WorkflowEngine
from services.legal_ai.agents.policies import PolicyEngine

def get_test_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def setup_agent_test_context(db: Session):
    org = db.query(Organization).filter(Organization.name == "Agent Test Org").first()
    if not org:
        org = Organization(name="Agent Test Org")
        db.add(org)
        db.commit()
        db.refresh(org)

    user = db.query(User).filter(User.email == "agent_tester@example.com").first()
    if not user:
        user = User(
            email="agent_tester@example.com",
            hashed_password="hashed",
            full_name="Agent Tester",
            organization_id=org.id,
            is_active=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    return org, user

def test_planner_intent_classification():
    db = next(get_test_db())
    org, user = setup_agent_test_context(db)
    
    orch = AgentOrchestratorV2(db)
    planner = orch.planner

    # 1. Test compliance query intent
    plan1 = planner.plan_query("Is this agreement compliant with RBI guidelines?")
    assert plan1["intent"] == "compliance_check"
    assert plan1["confidence_score"] >= 0.90
    assert "compliance_agent" in plan1["selected_agents"]
    assert len(plan1["subtasks"]) == 3

    # 2. Test risk query intent
    plan2 = planner.plan_query("Evaluate unlimited liability exposure risk.")
    assert plan2["intent"] == "risk_analysis"
    assert "risk_agent" in plan2["selected_agents"]

    # 3. Test clarification check (confidence < 0.70)
    plan3 = planner.plan_query("abc")
    assert plan3["confidence_score"] < 0.70
    assert plan3["intent"] == "clarification"

def test_policy_engine_enforcement():
    policy = {
        "allowed_organizations": [str(uuid.uuid4())],
        "allowed_tools": ["*"]
    }
    
    current_org = uuid.uuid4()
    with pytest.raises(Exception) as excinfo:
        PolicyEngine.validate_execution_policy(policy, str(current_org))
    assert "Organization context not authorized" in str(excinfo.value)

    policy_tool = {
        "allowed_organizations": [],
        "allowed_tools": ["policy_checker"],
        "allowed_models": ["*"]
    }
    with pytest.raises(Exception) as excinfo:
        PolicyEngine.validate_execution_policy(policy_tool, str(current_org), requested_tool="risk_calculator")
    assert "is not authorized for this agent" in str(excinfo.value)

def test_workflow_engine_retries_and_timeouts():
    db = next(get_test_db())
    org, user = setup_agent_test_context(db)
    
    context = SharedContext(db, user, org.id, [])
    engine = WorkflowEngine(context)

    calls = []
    
    def failing_task():
        calls.append(1)
        raise ValueError("Simulated transient runtime failure")

    with pytest.raises(RuntimeError) as excinfo:
        engine.execute_step_with_retry(
            step_id="failing_test_step",
            func=failing_task,
            max_retries=3,
            timeout_seconds=5
        )
    assert len(calls) == 3
    assert "failed after 3 attempts" in str(excinfo.value)

def test_full_orchestrator_workflow_execution():
    db = next(get_test_db())
    org, user = setup_agent_test_context(db)

    orch = AgentOrchestratorV2(db)
    
    res_generator = orch.execute_workflow(
        query="Run a GDPR compliance check on the active agreement.",
        current_user=user,
        document_ids=[]
    )
    
    res_list = list(res_generator)
    
    steps = [e.get("event") for e in res_list]
    assert "progress" in steps
    assert "workflow_completed" in steps
    
    completion = next(e for e in res_list if e.get("event") == "workflow_completed")
    assert "answer" in completion["data"]
    assert "explainability" in completion["data"]
    assert completion["data"]["explainability"]["intent_confidence"] >= 0.90
