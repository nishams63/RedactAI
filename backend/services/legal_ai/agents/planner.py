import logging
from typing import Dict, Any, List

logger = logging.getLogger("redactai.agents.planner")

class AgentPlanner:
    def __init__(self, registry):
        self.registry = registry

    def plan_query(self, query: str) -> Dict[str, Any]:
        """Classifies query intent, resolves capabilities, and builds a decomposed task plan."""
        query_lower = query.lower()
        
        intent = "general"
        confidence = 0.9
        reasoning = "Query handled by standard answering model."
        required_caps = ["text_generation"]
        alternatives = ["summary_agent"]

        if any(w in query_lower for w in ["comply", "compliance", "regulation", "gdpr", "dpdp", "hipaa", "rbi"]):
            intent = "compliance_check"
            confidence = 0.95
            reasoning = "Query mentions regulatory framework (GDPR/DPDP/HIPAA/RBI)."
            required_caps = ["regulatory_analysis"]
            alternatives = ["risk_agent"]
        elif any(w in query_lower for w in ["risk", "liability", "exposure", "indemnity", "unlimited"]):
            intent = "risk_analysis"
            confidence = 0.92
            reasoning = "Query asks about exposure, liability parameters, or risk levels."
            required_caps = ["risk_assessment"]
            alternatives = ["compliance_agent"]
        elif any(w in query_lower for w in ["summarize", "summary", "tldr", "executive summary"]):
            intent = "summarization"
            confidence = 0.98
            reasoning = "Query explicitly requests executive summary or text compression."
            required_caps = ["text_summarization"]
            alternatives = ["retrieval_agent"]

        if len(query.strip()) < 5:
            intent = "clarification"
            confidence = 0.4
            reasoning = "Query is too short or ambiguous to resolve intent."
            required_caps = []
            alternatives = []

        matched_agents = self.registry.discover_by_capability(required_caps)
        selected_agent_ids = [a.agent_id for a in matched_agents]

        subtasks = []
        if intent == "compliance_check":
            subtasks = [
                {"id": "retrieve", "capabilities": ["hybrid_retrieval"], "query": query},
                {"id": "compliance", "capabilities": ["regulatory_analysis"], "query": query},
                {"id": "citation", "capabilities": ["citation_verification"], "query": "Verify compliance citations"}
            ]
        elif intent == "risk_analysis":
            subtasks = [
                {"id": "retrieve", "capabilities": ["hybrid_retrieval"], "query": query},
                {"id": "risk", "capabilities": ["risk_assessment"], "query": query},
                {"id": "citation", "capabilities": ["citation_verification"], "query": "Verify risk calculations"}
            ]
        elif intent == "summarization":
            subtasks = [
                {"id": "retrieve", "capabilities": ["hybrid_retrieval"], "query": query},
                {"id": "summary", "capabilities": ["text_summarization"], "query": query}
            ]
        else:
            subtasks = [
                {"id": "retrieve", "capabilities": ["hybrid_retrieval"], "query": query}
            ]

        if confidence < 0.7:
            subtasks = [
                {"id": "clarify", "capabilities": ["human_review"], "query": "Requesting clarification due to low intent confidence."}
            ]

        return {
            "intent": intent,
            "confidence_score": confidence,
            "reasoning": reasoning,
            "selected_agents": selected_agent_ids,
            "alternative_agent_choices": alternatives,
            "subtasks": subtasks
        }
