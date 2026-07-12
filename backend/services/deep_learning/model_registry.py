"""
Model Registry — Level 2 Deep Learning Enhancement
Registers new Deep Learning architectures and swaps models dynamically
without modifications to downstream code or APIs.
"""
import logging
from typing import Dict, Type, Any

from services.deep_learning.interfaces import DocumentClassifier
from services.deep_learning.predictor import LegalBERTClassifier, LayoutLMClassifier

logger = logging.getLogger("redactai.dl.registry")


class DLModelRegistry:
    """Registry class managing swappable Deep Learning architectures."""

    _registry: Dict[str, Type[DocumentClassifier]] = {
        "legalbert": LegalBERTClassifier,
        "layoutlm": LayoutLMClassifier,
    }

    @classmethod
    def register_architecture(cls, name: str, classifier_cls: Type[DocumentClassifier]) -> None:
        """
        Dynamically register a new architecture class (e.g., RoBERTa, Llama, Gemma).
        Allows extending capabilities without changing base code.
        """
        name_lower = name.lower()
        cls._registry[name_lower] = classifier_cls
        logger.info(f"Registered new architecture class: {name} ({classifier_cls.__name__})")

    @classmethod
    def get_classifier(cls, model_type: str, **kwargs) -> DocumentClassifier:
        """
        Instantiate a swappable classifier based on registered model types.
        """
        model_type_lower = model_type.lower()
        
        # Support sub-string matching (e.g., 'nlpaueb/legal-bert-base-uncased' -> 'legalbert')
        selected_key = None
        for key in cls._registry.keys():
            if key in model_type_lower:
                selected_key = key
                break
                
        if not selected_key:
            # Default fallback to LegalBERT classifier for general transformers (RoBERTa, DeBERTa, etc.)
            logger.warning(f"Architecture '{model_type}' not directly registered. Falling back to default LegalBERTClassifier.")
            return LegalBERTClassifier(model_name=model_type, **kwargs)

        classifier_cls = cls._registry[selected_key]
        logger.info(f"Loading swappable classifier: {classifier_cls.__name__} for type {model_type}")
        return classifier_cls(model_name=model_type, **kwargs)
