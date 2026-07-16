from typing import List
from services.legal_ai.embeddings.base import BaseEmbeddingProvider
from services.legal_ai.embedder import LocalSentenceEmbedder

class MiniLMEmbeddingProvider(BaseEmbeddingProvider):
    def __init__(self):
        self.embedder = LocalSentenceEmbedder(model_name="sentence-transformers/all-MiniLM-L6-v2")

    def get_embedding(self, text: str) -> List[float]:
        return self.embedder.get_embedding(text)

    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        return self.embedder.get_embeddings(texts)

    @property
    def dimension(self) -> int:
        return 384
