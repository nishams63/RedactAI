import logging
from typing import Dict, Any
from services.ai.interfaces import OCRProvider, PIIProvider, NERProvider, LayoutProvider, LanguageProvider
from services.ai.providers import (
    PyMuPDFOCRProvider, FallbackOCRProvider,
    PresidioPIIProvider, SpacyNERProvider,
    PyMuPDFLayoutProvider, LangdetectLanguageProvider
)

logger = logging.getLogger("redactai.ai.registry")

class AIModelRegistry:
    """Registry to load and cache active AI/ML service providers."""
    
    def __init__(self):
        self._providers: Dict[str, Any] = {}
        # Pre-initialize and cache standard providers
        self._providers["language"] = LangdetectLanguageProvider()
        self._providers["layout"] = PyMuPDFLayoutProvider()
        self._providers["pii"] = PresidioPIIProvider()
        self._providers["ner"] = SpacyNERProvider()
        
        # Determine OCR provider
        self._providers["ocr_digital"] = PyMuPDFOCRProvider()
        self._providers["ocr_scanned"] = FallbackOCRProvider()

    def get_language_provider(self) -> LanguageProvider:
        return self._providers["language"]

    def get_layout_provider(self) -> LayoutProvider:
        return self._providers["layout"]

    def get_pii_provider(self) -> PIIProvider:
        return self._providers["pii"]

    def get_ner_provider(self) -> NERProvider:
        return self._providers["ner"]

    def get_ocr_provider(self, file_type: str) -> OCRProvider:
        """Return PyMuPDF provider for digital PDFs, and fallback/scanned for others."""
        if file_type == "Digital PDF":
            return self._providers["ocr_digital"]
        return self._providers["ocr_scanned"]


# Singleton instance
ai_registry = AIModelRegistry()
