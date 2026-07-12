from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class OCRProvider(ABC):
    """Abstract interface for Optical Character Recognition (OCR)."""
    @abstractmethod
    def extract_text(self, file_content: bytes, file_type: str) -> Dict[str, Any]:
        """Extract plain text, lines, words, coordinates, and page segmentation.
        
        Returns:
            Dict containing pages information, text, words with coordinates, etc.
        """
        pass

class PIIProvider(ABC):
    """Abstract interface for Personally Identifiable Information (PII) detection."""
    @abstractmethod
    def detect_pii(self, text: str, language: str = "en") -> List[Dict[str, Any]]:
        """Scan text and detect PII entities.
        
        Returns:
            List of detected entities with bounds, confidence, and type details.
        """
        pass

class NERProvider(ABC):
    """Abstract interface for Named Entity Recognition (NER)."""
    @abstractmethod
    def extract_entities(self, text: str) -> List[Dict[str, Any]]:
        """Extract standard named entities and domain-specific legal entities.
        
        Returns:
            List of detected named entities.
        """
        pass

class LayoutProvider(ABC):
    """Abstract interface for document layout analysis."""
    @abstractmethod
    def analyze_layout(self, file_content: bytes, file_type: str) -> List[Dict[str, Any]]:
        """Analyze page structure and detect layout blocks.
        
        Returns:
            List of blocks with block_type, coordinates, text, and page_number.
        """
        pass

class LanguageProvider(ABC):
    """Abstract interface for document language detection."""
    @abstractmethod
    def detect_language(self, text: str) -> str:
        """Detect the primary language of the text.
        
        Returns:
            Primary language name (e.g. English, Hindi, Tamil, etc.).
        """
        pass
