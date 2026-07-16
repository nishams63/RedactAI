from typing import List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from services.legal_ai.retrieval.vector import VectorRetrievalStrategy
from services.legal_ai.retrieval.bm25 import BM25RetrievalStrategy
from services.legal_ai.retrieval.rrf import ReciprocalRankFusion
from services.legal_ai.retrieval.reranker import CrossEncoderReranker
from services.legal_ai.embeddings.factory import EmbeddingProviderFactory

class HybridRetrievalStrategy:
    """Strategy wrapper executing sparse-dense search, merging results using RRF, and re-ranking."""
    def __init__(self, db_session: Session, embedding_model: str = "MiniLM"):
        self.vector_strategy = VectorRetrievalStrategy()
        self.bm25_strategy = BM25RetrievalStrategy(db_session)
        self.reranker = CrossEncoderReranker()
        self.embedder = EmbeddingProviderFactory.get_provider(embedding_model)

    def retrieve(self, query: str, document_id: str = None, top_k: int = 5) -> List[Tuple[Dict[str, Any], float]]:
        # 1. Fetch dense query vector embedding
        query_emb = self.embedder.get_embedding(query)
        
        # 2. Get dense candidate matches
        vector_candidates = self.vector_strategy.retrieve(query_emb, top_k=top_k * 3)
        
        # 3. Get sparse database keyword matches
        bm25_candidates = self.bm25_strategy.retrieve(query, document_id=document_id, top_k=top_k * 3)
        
        # 4. Perform rank fusion merging
        fused_candidates = ReciprocalRankFusion.fuse(vector_candidates, bm25_candidates, top_n=top_k * 2)
        
        # 5. Execute re-ranking
        reranked_candidates = self.reranker.rerank(query, fused_candidates)
        return reranked_candidates[:top_k]
