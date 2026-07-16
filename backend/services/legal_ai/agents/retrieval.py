from services.legal_ai.agents.base import BaseAgent
from typing import Dict, Any, List, Generator
from services.legal_ai.retrieval_pipeline import LegalRetrievalPipeline

class RetrievalAgent(BaseAgent):
    @property
    def agent_id(self) -> str:
        return "retrieval_agent"

    def process_task(
        self, 
        task_query: str, 
        history: List[Dict[str, Any]], 
        document_set: List[str], 
        preferences: Dict[str, Any],
        context_metadata: Dict[str, Any]
    ) -> Generator[Dict[str, Any], None, None]:
        db = context_metadata.get("db")
        yield {"event": "progress", "data": {"step": "retrieval_started", "document_ids": document_set}}
        
        pipeline = LegalRetrievalPipeline(db)
        
        retrieved_chunks = []
        for doc_id in document_set:
            chunks = pipeline.retrieve_context(
                query=task_query,
                document_id=doc_id,
                top_k=4
            )
            retrieved_chunks.extend(chunks)
            
        # Knowledge Graph Expansion and Traversal
        from services.legal_ai.graph_traversal import KnowledgeGraphTraversalEngine
        current_user = context_metadata.get("current_user")
        if current_user and db:
            yield {"event": "progress", "data": {"step": "graph_expansion_started"}}
            try:
                traversal_engine = KnowledgeGraphTraversalEngine(db, current_user.organization_id)
                query_terms = [t for t in task_query.split() if len(t) > 3]
                
                # Fetch key nodes using Personalized PageRank (PPR)
                top_nodes = traversal_engine.personalized_pagerank(query_terms)
                
                expanded_chunks = []
                traversed_paths = []
                
                for node in top_nodes[:3]:
                    # BFS neighbor expansion to depth 1
                    bfs_res = traversal_engine.bfs_traversal(node["id"], max_depth=1)
                    for n in bfs_res.get("nodes", []):
                        if n.get("type") == "Paragraph" and "text" in n.get("properties", {}):
                            p_text = n["properties"]["text"]
                            expanded_chunks.append({
                                "chunk_id": n["id"],
                                "text": f"[Graph Context - Entity: {node['label']} -> {n['label']}]: {p_text}",
                                "score": node.get("pagerank_score", 0.5) * 1.5,
                                "metadata": {
                                    "document_id": n.get("properties", {}).get("originating_document_id"),
                                    "page_number": n.get("properties", {}).get("page_number", 1),
                                    "source": "knowledge_graph"
                                }
                            })
                    traversed_paths.extend(bfs_res.get("explainability", []))
                    
                context_metadata["graph_traversal_paths"] = traversed_paths[:5]
                retrieved_chunks.extend(expanded_chunks)
                yield {"event": "progress", "data": {"step": "graph_expansion_completed", "expanded_count": len(expanded_chunks)}}
            except Exception as e:
                yield {"event": "progress", "data": {"step": "graph_expansion_failed", "error": str(e)}}
            
        if len(retrieved_chunks) > 1:
            retrieved_chunks = sorted(retrieved_chunks, key=lambda x: x.get("score", 0.0), reverse=True)
            
        yield {"event": "progress", "data": {"step": "retrieval_completed", "chunks_count": len(retrieved_chunks)}}
        yield {"event": "retrieved_context", "data": {"context_chunks": retrieved_chunks[:5]}}
