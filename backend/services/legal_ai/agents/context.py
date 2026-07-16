import time
import threading
from typing import Dict, Any, List
from sqlalchemy.orm import Session

class SharedContext:
    def __init__(self, db: Session, current_user: Any, organization_id: Any, active_documents: List[str]):
        self.db = db
        self.user = current_user
        self.org_id = organization_id
        self.active_documents = active_documents
        
        self._lock = threading.Lock()
        
        self.retrieved_chunks: List[Dict[str, Any]] = []
        self.extracted_entities: List[Dict[str, Any]] = []
        self.traversal_paths: List[str] = []
        self.workspace_items: List[Dict[str, Any]] = []
        
        self.task_memory: Dict[str, Any] = {}
        self.agent_memory: Dict[str, Any] = {}
        self.execution_logs: List[Dict[str, Any]] = []

    def log_execution_step(self, agent_id: str, message: str, status: str = "success", error: str | None = None):
        """Appends a thread-safe execution log line."""
        with self._lock:
            self.execution_logs.append({
                "agent_id": agent_id,
                "message": message,
                "status": status,
                "error": error,
                "timestamp": time.time()
            })

    def update_task_memory(self, key: str, value: Any):
        with self._lock:
            self.task_memory[key] = value

    def get_task_memory(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return self.task_memory.get(key, default)
