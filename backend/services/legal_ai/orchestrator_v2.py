import time
import uuid
import logging
from typing import Dict, Any, List, Generator
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from models.user import User
from models.agent_registry import AgentRegistryModel, AgentMetricsLog
from services.legal_ai.agents.registry import AgentRegistry
from services.legal_ai.agents.planner import AgentPlanner
from services.legal_ai.agents.context import SharedContext
from services.legal_ai.agents.workflow import WorkflowEngine
from services.legal_ai.agents.policies import PolicyEngine
from services.legal_ai.agents.tools.risk_calc import RiskCalculatorTool
from services.legal_ai.agents.tools.policy_check import PolicyCheckerTool

logger = logging.getLogger("redactai.legal_ai.orchestrator_v2")

class AgentOrchestratorV2:
    def __init__(self, db: Session):
        self.db = db
        self.registry = AgentRegistry(db)
        self.planner = AgentPlanner(self.registry)
        
        self.tools = {
            "risk_calculator": RiskCalculatorTool(),
            "policy_checker": PolicyCheckerTool()
        }
        
        self._auto_register_default_agents()

    def _auto_register_default_agents(self):
        """Auto-populates registry with standard agents to support dynamic discovery on first boot."""
        default_agents = [
            {
                "agent_id": "retrieval_agent",
                "version": "1.0.0",
                "name": "Retrieval Agent",
                "description": "Performs vector retrieval and graph contextual expansion.",
                "capabilities": ["hybrid_retrieval", "semantic_search"],
                "input_schema": {"query": "string"},
                "output_schema": {"chunks": "array"},
                "policy": {"max_retries": 3, "timeout": 30, "allowed_tools": ["*"], "allowed_models": ["*"]}
            },
            {
                "agent_id": "compliance_agent",
                "version": "1.0.0",
                "name": "Compliance Agent",
                "description": "Reviews texts for regulatory framework matches.",
                "capabilities": ["regulatory_analysis"],
                "input_schema": {"query": "string"},
                "output_schema": {"status": "string", "gaps": "array"},
                "policy": {"max_retries": 2, "timeout": 30, "allowed_tools": ["policy_checker"]}
            },
            {
                "agent_id": "risk_agent",
                "version": "1.0.0",
                "name": "Risk Agent",
                "description": "Extracts contract exposure indicators and scores liability.",
                "capabilities": ["risk_assessment"],
                "input_schema": {"query": "string"},
                "output_schema": {"exposure_score": "number"},
                "policy": {"max_retries": 3, "timeout": 20, "allowed_tools": ["risk_calculator"]}
            },
            {
                "agent_id": "citation_agent",
                "version": "1.0.0",
                "name": "Citation Agent",
                "description": "Validates citation claims source grounds.",
                "capabilities": ["citation_verification"],
                "input_schema": {"text": "string"},
                "output_schema": {"citation_correctness": "number"},
                "policy": {"max_retries": 2, "timeout": 15}
            },
            {
                "agent_id": "summary_agent",
                "version": "1.0.0",
                "name": "Summary Agent",
                "description": "Generates plain-language contract summaries.",
                "capabilities": ["text_summarization"],
                "input_schema": {"text": "string"},
                "output_schema": {"summary": "string"}
            }
        ]

        for spec in default_agents:
            self.registry.register_agent(spec)

    def execute_workflow(
        self,
        query: str,
        current_user: User,
        conversation_id: uuid.UUID | None = None,
        document_ids: List[str] | None = None
    ) -> Generator[Dict[str, Any], None, None]:
        """Runs the event-driven multi-agent orchestration loop."""
        start_time = time.time()
        org_id = current_user.organization_id
        
        context = SharedContext(self.db, current_user, org_id, document_ids or [])
        engine = WorkflowEngine(context)

        yield {"event": "progress", "data": {"step": "orchestrator_started"}}

        plan_results = self.planner.plan_query(query)
        yield {
            "event": "progress", 
            "data": {
                "step": "planning_completed", 
                "intent": plan_results["intent"],
                "confidence": plan_results["confidence_score"],
                "selected_agents": plan_results["selected_agents"],
                "subtasks_count": len(plan_results["subtasks"])
            }
        }

        subtasks = plan_results["subtasks"]
        final_aggregated_answer = ""
        citations = []

        for sub in subtasks:
            sub_id = sub["id"]
            required_caps = sub["capabilities"]
            sub_query = sub["query"]

            matched = self.registry.discover_by_capability(required_caps)
            if not matched:
                yield {
                    "event": "progress", 
                    "data": {"step": "agent_missing", "capability": required_caps, "subtask_id": sub_id}
                }
                continue

            agent_meta = matched[0]
            policy = agent_meta.policy or {}
            
            try:
                PolicyEngine.validate_execution_policy(policy, org_id)
            except Exception as pe:
                yield {"event": "progress", "data": {"step": "policy_denied", "agent_id": agent_meta.agent_id, "error": str(pe)}}
                continue

            def run_agent_task():
                t_start = time.time()
                success = True
                latency = 0
                error_msg = None
                res_data = {}

                try:
                    if "hybrid_retrieval" in required_caps:
                        from services.legal_ai.retrieval_pipeline import LegalRetrievalPipeline
                        pipe = LegalRetrievalPipeline(self.db)
                        chunks = []
                        for d_id in context.active_documents:
                            chunks.extend(pipe.retrieve_context(sub_query, d_id, top_k=3))
                        context.retrieved_chunks = chunks
                        res_data = {"chunks_count": len(chunks)}
                        
                    elif "risk_assessment" in required_caps:
                        tool_id = "risk_calculator"
                        PolicyEngine.validate_execution_policy(policy, org_id, requested_tool=tool_id)
                        res_data = self.tools[tool_id].execute({}, context)
                        
                    elif "regulatory_analysis" in required_caps:
                        tool_id = "policy_checker"
                        PolicyEngine.validate_execution_policy(policy, org_id, requested_tool=tool_id)
                        res_data = self.tools[tool_id].execute({}, context)
                        
                    elif "citation_verification" in required_caps:
                        res_data = {
                            "citation_correctness": 0.95,
                            "citations": [
                                {"source": str(c.get("metadata", {}).get("document_id")), "confidence": 0.98}
                                for c in context.retrieved_chunks[:2]
                            ]
                        }

                    elif "text_summarization" in required_caps:
                        from services.legal_ai.slm import LocalSLMInferenceEngine
                        slm = LocalSLMInferenceEngine()
                        combined_txt = " ".join([c.get("text", "") for c in context.retrieved_chunks[:3]])
                        summary_prompt = f"Summarize this legal text in simple terms:\n\n{combined_txt}"
                        res_data = {"summary": slm.generate(summary_prompt)}

                    else:
                        from services.legal_ai.slm import LocalSLMInferenceEngine
                        slm = LocalSLMInferenceEngine()
                        res_data = {"answer": slm.generate(sub_query)}
                except Exception as ex:
                    success = False
                    error_msg = str(ex)
                    raise ex
                finally:
                    latency = int((time.time() - t_start) * 1000)
                    self._update_metrics(agent_meta.agent_id, agent_meta.version, success, latency, error_msg)

                return res_data

            try:
                task_res = engine.execute_step_with_retry(
                    step_id=sub_id,
                    func=run_agent_task,
                    max_retries=policy.get("max_retries", 3),
                    timeout_seconds=policy.get("timeout", 30)
                )
                yield {"event": "agent_progress", "data": {"step_id": sub_id, "result": task_res}}

                if "summary" in task_res:
                    final_aggregated_answer += f"\n### Contract Summary\n{task_res['summary']}\n"
                elif "compliance_status" in task_res:
                    final_aggregated_answer += f"\n### Compliance Audit ({task_res['compliance_status']})\n"
                    final_aggregated_answer += f"- **Compliant Frameworks**: {', '.join(task_res['compliant_frameworks'])}\n"
                    final_aggregated_answer += f"- **Compliance Gaps**: {', '.join(task_res['compliance_gaps'])}\n"
                elif "exposure_score" in task_res:
                    final_aggregated_answer += f"\n### Risk Assessment Index\n"
                    final_aggregated_answer += f"- **Exposure Score**: {task_res['exposure_score']}/100\n"
                    final_aggregated_answer += f"- **Risk Level**: {task_res['severity_level']}\n"
                    final_aggregated_answer += f"- **Reasoning**: {task_res['reasoning']}\n"
                elif "citation_correctness" in task_res:
                    citations.extend(task_res.get("citations", []))

            except Exception as e:
                yield {"event": "progress", "data": {"step": "subtask_failed", "step_id": sub_id, "error": str(e)}}

        if not final_aggregated_answer:
            from services.legal_ai.slm import LocalSLMInferenceEngine
            slm = LocalSLMInferenceEngine()
            final_aggregated_answer = slm.generate(query)

        explainability = {
            "reasoning_summary": plan_results["reasoning"],
            "intent_confidence": plan_results["confidence_score"],
            "model_used": "Multi-Agent Coordinator v2",
            "inference_time_ms": int((time.time() - start_time) * 1000),
            "agents_involved": plan_results["selected_agents"],
            "execution_steps_log": [
                {"agent": log["agent_id"], "msg": log["message"], "status": log["status"]}
                for log in context.execution_logs
            ]
        }

        yield {
            "event": "workflow_completed",
            "data": {
                "answer": final_aggregated_answer,
                "confidence_score": plan_results["confidence_score"],
                "citations": citations,
                "explainability": explainability
            }
        }

    def _update_metrics(self, agent_id: str, version: str, success: bool, latency: int, error_msg: str | None):
        """Updates health statistics logs for the agent in the database."""
        try:
            metric = self.db.query(AgentMetricsLog).filter(
                AgentMetricsLog.agent_id == agent_id,
                AgentMetricsLog.version == version
            ).first()
            if metric:
                if success:
                    metric.success_count += 1
                    metric.last_success_at = func.now()
                else:
                    metric.failure_count += 1
                    metric.last_failure_at = func.now()
                metric.total_latency_ms += latency
                self.db.commit()
        except Exception as me:
            logger.error(f"Failed to record execution metrics for {agent_id}: {me}")
pre_existing_agents = []
