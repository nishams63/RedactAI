import abc
from typing import Dict, Any

class BaseTool(abc.ABC):
    """Abstract interface defining standard schemas and execution paradigms for LLM tools."""
    
    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Unique identifier of the tool."""
        pass

    @property
    @abc.abstractmethod
    def description(self) -> str:
        """Detailed documentation explaining when the orchestrator should trigger the tool."""
        pass

    @property
    @abc.abstractmethod
    def parameters_schema(self) -> Dict[str, Any]:
        """JSON-schema definition matching arguments expected by the run method."""
        pass

    @abc.abstractmethod
    def run(self, arguments: Dict[str, Any], context_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Executes the tool's core legal reasoning logic."""
        pass
