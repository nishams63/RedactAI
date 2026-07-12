import importlib
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("redactai.dependencies")

# Allow dynamic overrides for automated simulation testing
_MOCK_OVERRIDES = {}

class DependencyStatus:
    def __init__(self, name: str, fallback_available: bool = False):
        self.name = name
        self.fallback_available = fallback_available

    @property
    def installed(self) -> bool:
        if self.name in _MOCK_OVERRIDES:
            return _MOCK_OVERRIDES[self.name]
        try:
            importlib.import_module(self.name)
            return True
        except (ImportError, ModuleNotFoundError, Exception):
            return False

    @property
    def version(self) -> Optional[str]:
        if self.name in _MOCK_OVERRIDES and not _MOCK_OVERRIDES[self.name]:
            return None
        try:
            module = importlib.import_module(self.name)
            if hasattr(module, "__version__"):
                return getattr(module, "__version__")
            return "Loaded"
        except Exception:
            return None

    @property
    def availability(self) -> str:
        return "Available" if self.installed else "Unavailable"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "installed": self.installed,
            "version": self.version,
            "availability": self.availability,
            "fallback_available": self.fallback_available
        }

class OptionalDependencyManager:
    _dependencies = {
        "torch": DependencyStatus("torch", fallback_available=True),
        "transformers": DependencyStatus("transformers", fallback_available=True),
        "sentence_transformers": DependencyStatus("sentence_transformers", fallback_available=True),
        "onnxruntime": DependencyStatus("onnxruntime", fallback_available=True),
        "xgboost": DependencyStatus("xgboost", fallback_available=True),
        "spacy": DependencyStatus("spacy", fallback_available=True),
        "easyocr": DependencyStatus("easyocr", fallback_available=True),
        "paddleocr": DependencyStatus("paddleocr", fallback_available=True),
        "reportlab": DependencyStatus("reportlab", fallback_available=True),
    }

    @classmethod
    def get_status(cls, name: str) -> Optional[DependencyStatus]:
        return cls._dependencies.get(name)

    @classmethod
    def is_installed(cls, name: str) -> bool:
        dep = cls.get_status(name)
        return dep.installed if dep else False

    @classmethod
    def get_all_status(cls) -> Dict[str, Dict[str, Any]]:
        return {
            name: dep.to_dict()
            for name, dep in cls._dependencies.items()
        }
