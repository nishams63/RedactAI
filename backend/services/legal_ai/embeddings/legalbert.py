import hashlib
import numpy as np
from typing import List
from services.legal_ai.embeddings.base import BaseEmbeddingProvider
from services.legal_ai.embedder import LocalSentenceEmbedder

class LegalBERTEmbeddingProvider(BaseEmbeddingProvider):
    def __init__(self):
        # We target LegalBERT base dimension 768
        self.embedder = LocalSentenceEmbedder(model_name="sentence-transformers/all-MiniLM-L6-v2")

    def get_embedding(self, text: str) -> List[float]:
        # Emulate 768-dim LegalBERT vector
        np.random.seed(int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:8], 16) % (2**32))
        emb = np.random.normal(0, 1, 768)
        return (emb / np.linalg.norm(emb)).tolist()

    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        return [self.get_embedding(t) for t in texts]

    @property
    def dimension(self) -> int:
        return 768
