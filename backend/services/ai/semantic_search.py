"""Module 6 - Semantic Search.

Provides vector indexing and semantic retrieval for document text blocks and clauses.
Uses LocalSentenceEmbedder and ChromaVectorStore (or NumpyVectorStore fallback).
"""
import uuid
import logging
from typing import Dict, Any, List, Tuple
from services.legal_ai.embedder import LocalSentenceEmbedder
from services.legal_ai.vector_store import ChromaVectorStore

logger = logging.getLogger("redactai.ai.semantic_search")

class LegalSemanticSearchEngine:
    def __init__(self):
        self.embedder = LocalSentenceEmbedder()
        # Initialize chroma collection specifically for document clauses
        self.vector_store = ChromaVectorStore(collection_name="document_clauses")

    def index_document(self, document_id: uuid.UUID, organization_id: uuid.UUID, blocks: List[Dict[str, Any]]) -> bool:
        """Encodes all structural text blocks of a document and indexes them in the vector store."""
        if not blocks:
            logger.warning(f"No blocks to index for document {document_id}")
            return False

        logger.info(f"Indexing document {document_id} (org: {organization_id}) with {len(blocks)} text blocks...")
        try:
            chunks = []
            texts = []
            
            for idx, block in enumerate(blocks):
                text = block.get("text", "").strip()
                if not text or len(text) < 15: # Skip very short snippets/whitespace
                    continue
                
                chunk_id = f"{document_id}_{block.get('page_number', 1)}_{idx}"
                metadata = {
                    "document_id": str(document_id),
                    "organization_id": str(organization_id),
                    "page_number": int(block.get("page_number", 1)),
                    "block_type": block.get("block_type", "Paragraph")
                }
                chunks.append({
                    "chunk_id": chunk_id,
                    "text": text,
                    "metadata": metadata
                })
                texts.append(text)
                
            if not chunks:
                return True

            # Generate embeddings in optimized batch
            embeddings = self.embedder.get_embeddings(texts)
            
            # Store in vector store
            self.vector_store.add_chunks(chunks, embeddings)
            logger.info(f"Indexed {len(chunks)} text chunks for document {document_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to index document {document_id}: {e}")
            return False

    def search_document(self, document_id: uuid.UUID, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Queries the vector store for similar clauses within a single document."""
        if not query or not query.strip():
            return []

        try:
            query_emb = self.embedder.get_embedding(query)
            # Retrieve slightly more than top_k for Python-side filtering
            results = self.vector_store.query(query_emb, top_k=max(100, top_k * 10))
            
            filtered_results = []
            for chunk, score in results:
                meta = chunk.get("metadata", {})
                if meta.get("document_id") == str(document_id):
                    filtered_results.append({
                        "text": chunk["text"],
                        "page_number": meta.get("page_number"),
                        "block_type": meta.get("block_type"),
                        "score": round(score, 4)
                    })
                    if len(filtered_results) >= top_k:
                        break
            return filtered_results
        except Exception as e:
            logger.error(f"Semantic search failed for document {document_id}: {e}")
            return []

    def search_organization(self, organization_id: uuid.UUID, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """Queries the vector store for similar clauses across all organization documents."""
        if not query or not query.strip():
            return []

        try:
            query_emb = self.embedder.get_embedding(query)
            results = self.vector_store.query(query_emb, top_k=max(100, top_k * 10))
            
            filtered_results = []
            for chunk, score in results:
                meta = chunk.get("metadata", {})
                if meta.get("organization_id") == str(organization_id):
                    filtered_results.append({
                        "text": chunk["text"],
                        "document_id": meta.get("document_id"),
                        "page_number": meta.get("page_number"),
                        "block_type": meta.get("block_type"),
                        "score": round(score, 4)
                    })
                    if len(filtered_results) >= top_k:
                        break
            return filtered_results
        except Exception as e:
            logger.error(f"Global semantic search failed for organization {organization_id}: {e}")
            return []

semantic_search_engine = LegalSemanticSearchEngine()
