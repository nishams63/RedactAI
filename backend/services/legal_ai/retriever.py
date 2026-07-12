import json
from typing import List, Dict, Any, Tuple
from services.legal_ai.knowledge_base.loader import KnowledgeIngestionPipeline
from services.legal_ai.embedder import LocalSentenceEmbedder
from services.legal_ai.vector_store import ChromaVectorStore
from services.legal_ai.cache_manager import CacheManager

class LegalRetriever:
    def __init__(self, kb_version: str = "v1.0.0"):
        self.kb_version = kb_version
        self.pipeline = KnowledgeIngestionPipeline()
        self.embedder = LocalSentenceEmbedder()
        self.vector_store = ChromaVectorStore()
        self.cache_manager = CacheManager()
        self._sync_index()

    def _sync_index(self):
        """Lazy-syncs vector database index with all chunks loaded from pipeline version."""
        chunks = self.pipeline.get_active_chunks(self.kb_version)
        if not chunks:
            return
            
        # Check if vector store is already populated (or fallback store)
        # Simply re-add chunks to guarantee they exist (the add_chunks method deduplicates by chunk_id)
        embeddings = self.embedder.get_embeddings([c["text"] for c in chunks])
        self.vector_store.add_chunks(chunks, embeddings)

    def retrieve(self, query: str, top_k: int = 4, metadata_filter: Dict[str, Any] = None) -> List[Tuple[Dict[str, Any], float]]:
        """Retrieve most semantically relevant legal chunks with metadata filtering, hybrid boosting, and score normalization."""
        # 1. Check retrieval cache
        cache_key = f"{query}_{top_k}_{json.dumps(metadata_filter, sort_keys=True) if metadata_filter else ''}"
        cached = self.cache_manager.get("retrieval", cache_key)
        if cached:
            # Map cached lists of [chunk, score] to list of tuples (chunk, score)
            return [(item[0], item[1]) for item in cached]

        query_emb = self.embedder.get_embedding(query)
        
        # Pull a slightly larger set of candidates first to allow filtering
        candidate_count = top_k * 3 if metadata_filter else top_k
        results = self.vector_store.query(query_emb, top_k=candidate_count)
        
        # Apply metadata filtering
        filtered_results = []
        for chunk, score in results:
            keep = True
            if metadata_filter:
                meta = chunk.get("metadata", {})
                for k, v in metadata_filter.items():
                    if meta.get(k) != v:
                        keep = False
                        break
            if keep:
                filtered_results.append((chunk, score))

        # Apply hybrid keyword booster: boost score slightly if keyword matches
        boosted_results = []
        query_words = set(query.lower().split())
        for chunk, score in filtered_results:
            boost = 0.0
            meta = chunk.get("metadata", {})
            keywords = meta.get("keywords", [])
            
            # Boost score based on overlapping keywords
            overlap = len(query_words.intersection(set([k.lower() for k in keywords])))
            if overlap > 0:
                boost = min(0.15, overlap * 0.05)
                
            boosted_score = score + boost
            boosted_results.append((chunk, boosted_score))
            
        # Re-sort desc
        boosted_results.sort(key=lambda x: x[1], reverse=True)
        final_candidates = boosted_results[:top_k]

        # Apply Min-Max score normalization if we have multiple candidates
        if len(final_candidates) > 1:
            scores = [x[1] for x in final_candidates]
            min_s, max_s = min(scores), max(scores)
            normalized_results = []
            for chunk, score in final_candidates:
                if max_s - min_s > 0:
                    norm_score = 0.3 + 0.68 * ((score - min_s) / (max_s - min_s))
                else:
                    norm_score = max(0.0, min(1.0, score))
                normalized_results.append((chunk, round(norm_score, 2)))
            self.cache_manager.set("retrieval", cache_key, normalized_results)
            return normalized_results
        elif len(final_candidates) == 1:
            chunk, score = final_candidates[0]
            val = [(chunk, round(max(0.0, min(0.98, score)), 2))]
            self.cache_manager.set("retrieval", cache_key, val)
            return val
            
        return []
