"""
Inference Interfaces — Level 2 Deep Learning Enhancement
Provides a common service interface for Swappable Document Classifiers.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List


class DocumentClassifier(ABC):
    """Abstract interface for all document sensitivity classifiers."""

    @abstractmethod
    def predict(self, features: Dict[str, Any], text: str) -> Dict[str, Any]:
        """
        Run inference on a single document.

        Args:
            features: Dictionary of extracted ML features (~50 features).
            text: Raw text of the document.

        Returns:
            Dict containing:
                - predicted_class: str
                - confidence: float
                - probabilities: Dict[str, float]
        """
        pass

    @abstractmethod
    def predict_batch(self, batch: List[Dict[str, Any]], texts: List[str]) -> List[Dict[str, Any]]:
        """
        Run efficient batched inference on multiple documents.

        Args:
            batch: List of feature dictionaries.
            texts: List of raw document texts.

        Returns:
            List of prediction dictionaries.
        """
        pass
