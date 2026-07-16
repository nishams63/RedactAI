from services.legal_ai.agents.base import BaseAgent
from typing import Dict, Any, List, Generator

class ReviewAgent(BaseAgent):
    @property
    def agent_id(self) -> str:
        return "review_agent"

    def process_task(
        self, 
        task_query: str, 
        history: List[Dict[str, Any]], 
        document_set: List[str], 
        preferences: Dict[str, Any],
        context_metadata: Dict[str, Any]
    ) -> Generator[Dict[str, Any], None, None]:
        yield {"event": "progress", "data": {"step": "review_orchestration_started"}}
        
        confidence_score = context_metadata.get("confidence_score", 1.0)
        threshold = preferences.get("confidence_threshold", 0.70)
        
        needs_review = confidence_score < threshold
        
        yield {"event": "progress", "data": {"step": "review_orchestration_completed"}}
        yield {"event": "review_status", "data": {"needs_review": needs_review, "confidence_score": confidence_score}}
