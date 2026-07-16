from services.legal_ai.agents.base import BaseAgent
from typing import Dict, Any, List, Generator
from services.legal_ai.tools.summarizer import ContractSummarizerTool

class SummaryAgent(BaseAgent):
    @property
    def agent_id(self) -> str:
        return "summary_agent"

    def process_task(
        self, 
        task_query: str, 
        history: List[Dict[str, Any]], 
        document_set: List[str], 
        preferences: Dict[str, Any],
        context_metadata: Dict[str, Any]
    ) -> Generator[Dict[str, Any], None, None]:
        yield {"event": "progress", "data": {"step": "summary_generation_started"}}
        
        context_chunks = context_metadata.get("context_chunks", [])
        combined_text = "\n\n".join([c["text"] for c in context_chunks]) if context_chunks else task_query
        
        summarizer = ContractSummarizerTool()
        result = summarizer.run(
            arguments={"context": combined_text},
            context_metadata=context_metadata
        )
        
        yield {"event": "progress", "data": {"step": "summary_generation_completed"}}
        yield {"event": "summary_report", "data": result}
