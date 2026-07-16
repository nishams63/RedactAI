import time
import logging
import concurrent.futures
from typing import Dict, Any, List, Callable
from services.legal_ai.agents.context import SharedContext
from services.legal_ai.agents.event_bus import event_bus

logger = logging.getLogger("redactai.agents.workflow")

class WorkflowEngine:
    def __init__(self, shared_context: SharedContext):
        self.context = shared_context
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=5)

    def execute_step_with_retry(
        self, 
        step_id: str, 
        func: Callable[[], Dict[str, Any]], 
        max_retries: int = 3, 
        timeout_seconds: int = 30
    ) -> Dict[str, Any]:
        """Runs a step function with retries and timeout boundaries."""
        event_bus.publish("TaskStarted", {"step_id": step_id})
        self.context.log_execution_step(step_id, f"Started execution of {step_id}", "running")
        
        attempt = 0
        backoff = 1.0

        while attempt < max_retries:
            attempt += 1
            future = self.executor.submit(func)
            try:
                result = future.result(timeout=timeout_seconds)
                event_bus.publish("TaskCompleted", {"step_id": step_id, "result": result})
                self.context.log_execution_step(step_id, f"Completed execution of {step_id}", "success")
                return result
            except concurrent.futures.TimeoutError:
                logger.warning(f"Timeout exceeded for step {step_id} (Attempt {attempt}/{max_retries}).")
                event_bus.publish("TaskFailed", {"step_id": step_id, "error": "Timeout exceeded"})
                self.context.log_execution_step(step_id, f"Timeout on {step_id}", "failed", "Timeout exceeded")
            except Exception as e:
                logger.error(f"Error in step {step_id} execution: {e}")
                event_bus.publish("TaskFailed", {"step_id": step_id, "error": str(e)})
                self.context.log_execution_step(step_id, f"Error in execution of {step_id}", "failed", str(e))
                
            if attempt < max_retries:
                event_bus.publish("RetryRequested", {"step_id": step_id, "attempt": attempt})
                time.sleep(backoff)
                backoff *= 2.0

        raise RuntimeError(f"Step {step_id} failed after {max_retries} attempts.")

    def execute_parallel(self, steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Executes multiple tasks concurrently using ThreadPoolExecutor worker slots."""
        futures = []
        for s in steps:
            step_id = s["id"]
            func = s["func"]
            max_retries = s.get("max_retries", 3)
            timeout = s.get("timeout", 30)
            
            future = self.executor.submit(
                self.execute_step_with_retry, step_id, func, max_retries, timeout
            )
            futures.append(future)

        results = []
        for fut in concurrent.futures.as_completed(futures):
            try:
                results.append(fut.result())
            except Exception as e:
                logger.error(f"Parallel job failed: {e}")
                
        return results
