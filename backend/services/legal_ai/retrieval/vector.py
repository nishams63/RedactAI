from typing import List, Dict, Any, Tuple
from services.legal_ai.vector_store import ChromaVectorStore

class VectorRetrievalStrategy:
    def __init__(self, collection_name: str = "document_clauses"):
        self.vector_store = ChromaVectorStore(collection_name=collection_name)

    def retrieve(self, query_embedding: List[float], top_k: int = 5) -> List[Tuple[Dict[str, Any], float]]:
        return self.vector_store.query(query_embedding, top_k=top_k)
