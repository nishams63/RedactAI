from services.legal_ai.agents.base import BaseAgent
from typing import Dict, Any, List, Generator
from services.legal_ai.tools.citation_validator import CitationValidatorTool

class CitationAgent(BaseAgent):
    @property
    def agent_id(self) -> str:
        return "citation_agent"

    def process_task(
        self, 
        task_query: str, 
        history: List[Dict[str, Any]], 
        document_set: List[str], 
        preferences: Dict[str, Any],
        context_metadata: Dict[str, Any]
    ) -> Generator[Dict[str, Any], None, None]:
        yield {"event": "progress", "data": {"step": "citation_validation_started"}}
        
        answer_text = context_metadata.get("answer_text", "")
        context_chunks = context_metadata.get("context_chunks", [])
        
        validator = CitationValidatorTool()
        result = validator.run(
            arguments={"claim": answer_text, "retrieved_context": context_chunks},
            context_metadata=context_metadata
        )
        
        yield {"event": "progress", "data": {"step": "citation_validation_completed"}}
        yield {"event": "citations_verified", "data": result}
