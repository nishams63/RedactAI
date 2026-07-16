import time
from typing import Any, Dict

class SimpleTTLCache:
    def __init__(self, default_ttl_seconds: int = 300):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.ttl = default_ttl_seconds

    def set(self, key: str, value: Any):
        self.cache[key] = {
            "value": value,
            "expires_at": time.time() + self.ttl
        }

    def get(self, key: str) -> Any | None:
        if key not in self.cache:
            return None
        item = self.cache[key]
        if time.time() > item["expires_at"]:
            del self.cache[key]
            return None
        return item["value"]

    def clear(self):
        self.cache.clear()

graph_cache = SimpleTTLCache()
