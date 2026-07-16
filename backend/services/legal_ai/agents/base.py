import abc
from typing import Dict, Any, List, Generator

class BaseAgent(abc.ABC):
    """Abstract class for independent sub-agents operating within the Copilot workspace."""

    @property
    @abc.abstractmethod
    def agent_id(self) -> str:
        pass

    @abc.abstractmethod
    def process_task(
        self, 
        task_query: str, 
        history: List[Dict[str, Any]], 
        document_set: List[str], 
        preferences: Dict[str, Any],
        context_metadata: Dict[str, Any]
    ) -> Generator[Dict[str, Any], None, None]:
        """Runs agent loop, yielding SSE token fragments or progress events."""
        pass
