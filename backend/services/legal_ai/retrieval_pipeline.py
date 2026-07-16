from typing import List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from services.legal_ai.retrieval.hybrid import HybridRetrievalStrategy
from models.rag import RAGChunk

class LegalRetrievalPipeline:
    """Retrieval Pipeline coordinating hybrid strategy, metadata filters, context expansion, and reranking."""
    def __init__(self, db_session: Session, embedding_model: str = "MiniLM"):
        self.db = db_session
        self.hybrid_strategy = HybridRetrievalStrategy(db_session, embedding_model=embedding_model)

    def _expand_context(self, chunk: Dict[str, Any], expansion_range: int = 1) -> str:
        """Retrieves adjacent chunks in the same document to expand the context window size."""
        meta = chunk.get("metadata", {})
        doc_id = meta.get("document_id")
        p_num = meta.get("page_number")
        
        if not doc_id or not p_num:
            return chunk.get("text", "")

        # Fetch chunks from the same document and page to merge
        adjacent_chunks = self.db.query(RAGChunk).filter(
            RAGChunk.document_id == doc_id,
            RAGChunk.page_number == p_num,
            RAGChunk.status == "Active"
        ).order_by(RAGChunk.created_at.asc()).all()

        if adjacent_chunks:
            # Merge adjacent texts sequentially
            texts = [c.text for c in adjacent_chunks]
            return "\n".join(texts)
            
        return chunk.get("text", "")

    def retrieve_context(
        self, 
        query: str, 
        document_id: str = None, 
        metadata_filters: Dict[str, Any] = None, 
        top_k: int = 4
    ) -> List[Dict[str, Any]]:
        """Executes retrieval pipeline, applying metadata filtering, context expansion, and returning context blocks."""
        # 1. Retrieve candidates via strategy
        candidates = self.hybrid_strategy.retrieve(query, document_id=document_id, top_k=top_k * 2)

        # 2. Apply metadata filters Python-side to ensure strict compliance
        filtered = []
        for chunk, score in candidates:
            keep = True
            meta = chunk.get("metadata", {})
            
            if metadata_filters:
                for k, v in metadata_filters.items():
                    # E.g. date year, department, client matches
                    if meta.get(k) != v and chunk.get(k) != v:
                        keep = False
                        break
            if keep:
                filtered.append((chunk, score))

        # 3. Context Expansion & Formatted Packaging
        final_context_blocks = []
        for chunk, score in filtered[:top_k]:
            expanded_text = self._expand_context(chunk)
            
            # Combine back metadata keys
            meta = chunk.get("metadata", {})
            final_context_blocks.append({
                "chunk_id": chunk["chunk_id"],
                "text": expanded_text,
                "score": score,
                "metadata": {
                    "document_id": meta.get("document_id"),
                    "page_number": meta.get("page_number", 1),
                    "chunk_type": meta.get("chunk_type", "paragraph"),
                    "document_title": meta.get("document_title", "Contract Reference")
                }
            })

        return final_context_blocks
