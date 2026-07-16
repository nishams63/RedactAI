from services.legal_ai.embeddings.minilm import MiniLMEmbeddingProvider
from services.legal_ai.embeddings.legalbert import LegalBERTEmbeddingProvider
from services.legal_ai.embeddings.bge import BGEEmbeddingProvider

class EmbeddingProviderFactory:
    @staticmethod
    def get_provider(model_name: str):
        name_lower = model_name.lower()
        if "minilm" in name_lower:
            return MiniLMEmbeddingProvider()
        elif "legalbert" in name_lower or "legal-bert" in name_lower:
            return LegalBERTEmbeddingProvider()
        elif "bge" in name_lower:
            return BGEEmbeddingProvider()
        else:
            # Default fallback
            return MiniLMEmbeddingProvider()
