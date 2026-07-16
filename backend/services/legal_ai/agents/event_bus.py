import logging
from typing import Dict, Any, List, Callable

logger = logging.getLogger("redactai.agents.event_bus")

class EventBus:
    def __init__(self):
        self._subscribers: Dict[str, List[Callable[[Dict[str, Any]], None]]] = {}

    def subscribe(self, event_type: str, callback: Callable[[Dict[str, Any]], None]):
        """Subscribe to a specific agent execution event."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)

    def publish(self, event_type: str, data: Dict[str, Any]):
        """Broadcasts event payload to all registered subscribers."""
        subscribers = self._subscribers.get(event_type, [])
        if not subscribers:
            return
            
        logger.debug(f"EventBus publishing '{event_type}' payload.")
        for cb in subscribers:
            try:
                cb(data)
            except Exception as e:
                logger.error(f"Error in EventBus subscriber callback: {e}")

event_bus = EventBus()
