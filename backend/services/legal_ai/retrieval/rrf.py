from typing import List, Dict, Any, Tuple

class ReciprocalRankFusion:
    """Aggregates and merges multi-source lists using Reciprocal Rank Fusion (RRF)."""
    @staticmethod
    def fuse(
        vector_results: List[Tuple[Dict[str, Any], float]], 
        bm25_results: List[Tuple[Dict[str, Any], float]], 
        k: int = 60, 
        top_n: int = 5
    ) -> List[Tuple[Dict[str, Any], float]]:
        scores = {}
        
        # Process Vector candidates rank
        for rank, (chunk, _) in enumerate(vector_results):
            cid = chunk["chunk_id"]
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank + 1)
            scores[cid + "_chunk"] = chunk

        # Process BM25 candidates rank
        for rank, (chunk, _) in enumerate(bm25_results):
            cid = chunk["chunk_id"]
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank + 1)
            scores[cid + "_chunk"] = chunk

        # Sort candidate IDs based on RRF scores
        sorted_ids = sorted(
            [item for item in scores.keys() if not item.endswith("_chunk")], 
            key=lambda x: scores[x], 
            reverse=True
        )
        
        results = []
        for cid in sorted_ids[:top_n]:
            results.append((scores[cid + "_chunk"], round(scores[cid], 4)))
        return results
