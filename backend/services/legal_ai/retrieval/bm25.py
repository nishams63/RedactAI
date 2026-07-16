from typing import List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from models.rag import RAGChunk

class BM25RetrievalStrategy:
    """Sparse term matching retrieval strategy using database queries."""
    def __init__(self, db_session: Session):
        self.db = db_session

    def retrieve(self, query: str, document_id: str = None, top_k: int = 5) -> List[Tuple[Dict[str, Any], float]]:
        query_terms = [t.lower() for t in query.split() if len(t) > 2]
        if not query_terms:
            return []

        chunks_query = self.db.query(RAGChunk).filter(RAGChunk.status == "Active")
        if document_id:
            chunks_query = chunks_query.filter(RAGChunk.document_id == document_id)
        chunks = chunks_query.all()
        
        results = []
        for c in chunks:
            score = 0.0
            text_lower = c.text.lower()
            for term in query_terms:
                tf = text_lower.count(term)
                if tf > 0:
                    score += (tf * 1.5) / (tf + 0.5)  # Mimic BM25 term saturation formula
            if score > 0:
                chunk_dict = {
                    "chunk_id": str(c.id),
                    "text": c.text,
                    "metadata": {
                        "document_id": str(c.document_id),
                        "page_number": c.page_number,
                        "chunk_type": c.chunk_type
                    }
                }
                results.append((chunk_dict, round(score, 4)))
                
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]
