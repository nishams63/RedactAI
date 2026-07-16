import abc
from typing import Dict, Any
from services.legal_ai.agents.context import SharedContext

class BaseTool(abc.ABC):
    @property
    @abc.abstractmethod
    def tool_id(self) -> str:
        pass

    @abc.abstractmethod
    def execute(self, inputs: Dict[str, Any], context: SharedContext) -> Dict[str, Any]:
        """Perform dedicated unit execution task, returning payload dict."""
        pass
