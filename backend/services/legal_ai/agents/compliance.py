from services.legal_ai.agents.base import BaseAgent
from typing import Dict, Any, List, Generator
from services.legal_ai.tools.compliance_checker import ComplianceCheckerTool

class ComplianceAgent(BaseAgent):
    @property
    def agent_id(self) -> str:
        return "compliance_agent"

    def process_task(
        self, 
        task_query: str, 
        history: List[Dict[str, Any]], 
        document_set: List[str], 
        preferences: Dict[str, Any],
        context_metadata: Dict[str, Any]
    ) -> Generator[Dict[str, Any], None, None]:
        yield {"event": "progress", "data": {"step": "compliance_eval_started"}}
        
        context_chunks = context_metadata.get("context_chunks", [])
        combined_text = "\n\n".join([c["text"] for c in context_chunks]) if context_chunks else task_query
        
        checker = ComplianceCheckerTool()
        result = checker.run(
            arguments={"clause_text": combined_text, "regulations": preferences.get("regulations", "DPDP Act 2023")},
            context_metadata=context_metadata
        )
        
        yield {"event": "progress", "data": {"step": "compliance_eval_completed"}}
        yield {"event": "compliance_report", "data": result}
