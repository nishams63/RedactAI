from typing import List, Dict, Any, Tuple

class CrossEncoderReranker:
    """Reranks candidate results using token overlap (Jaccard similarity index) as proxy."""
    def rerank(self, query: str, candidates: List[Tuple[Dict[str, Any], float]]) -> List[Tuple[Dict[str, Any], float]]:
        query_words = set(query.lower().split())
        if not query_words:
            return candidates

        reranked = []
        for chunk, base_score in candidates:
            text_val = chunk.get("text", "")
            chunk_words = set(text_val.lower().split())
            intersection = query_words.intersection(chunk_words)
            union = query_words.union(chunk_words)
            jaccard = len(intersection) / (len(union) + 1e-9)
            
            # Combine original score (e.g. 70% weight) and jaccard (30% weight)
            combined = base_score * 0.7 + jaccard * 0.3
            reranked.append((chunk, round(combined, 4)))
            
        reranked.sort(key=lambda x: x[1], reverse=True)
        return reranked
