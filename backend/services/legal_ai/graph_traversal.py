import uuid
import logging
from typing import Dict, Any, List, Set, Tuple
from sqlalchemy.orm import Session
from models.graph import GraphNode, GraphEdge

try:
    import networkx as nx
    _HAS_NETWORKX = True
except ImportError:
    nx = None
    _HAS_NETWORKX = False
    logging.getLogger("redactai").warning("networkx not installed. Knowledge graph traversal features will be unavailable.")

class KnowledgeGraphTraversalEngine:
    def __init__(self, db: Session, organization_id: uuid.UUID):
        self.db = db
        self.org_id = organization_id

    def load_networkx_graph(self, document_version_id: uuid.UUID | None = None):
        """Loads nodes and edges matching the tenant/organization into a NetworkX DiGraph."""
        if not _HAS_NETWORKX:
            return None
        from services.legal_ai.graph_cache import graph_cache
        cache_key = f"graph_{self.org_id}_{document_version_id}"
        cached = graph_cache.get(cache_key)
        if cached is not None:
            return cached

        G = nx.DiGraph()
        
        node_query = self.db.query(GraphNode).filter(GraphNode.organization_id == self.org_id)
        if document_version_id:
            node_query = node_query.filter(GraphNode.document_version_id == document_version_id)
        nodes = node_query.all()
        
        edge_query = self.db.query(GraphEdge).filter(GraphEdge.organization_id == self.org_id)
        if document_version_id:
            edge_query = edge_query.filter(GraphEdge.document_version_id == document_version_id)
        edges = edge_query.all()

        for n in nodes:
            G.add_node(
                str(n.id),
                label=n.label,
                type=n.node_type,
                properties=n.properties or {}
            )
            
        for e in edges:
            G.add_edge(
                str(e.source_node_id),
                str(e.target_node_id),
                id=str(e.id),
                relation=e.relationship_type,
                weight=e.weight,
                confidence=e.confidence_score,
                properties=e.properties or {}
            )
            
        graph_cache.set(cache_key, G)
        return G

    def bfs_traversal(
        self, 
        start_node_id: str, 
        max_depth: int = 2, 
        document_version_id: uuid.UUID | None = None
    ) -> Dict[str, Any]:
        """Breadth First Search traversal tracing pathways and node sequences."""
        G = self.load_networkx_graph(document_version_id)
        if G is None or start_node_id not in G:
            return {"nodes": [], "edges": [], "explainability": []}

        visited_nodes = {}
        visited_edges = []
        queue = [(start_node_id, 0)]
        visited_nodes[start_node_id] = 0

        while queue:
            curr, depth = queue.pop(0)
            if depth >= max_depth:
                continue

            for neighbor in G.successors(curr):
                if neighbor not in visited_nodes:
                    visited_nodes[neighbor] = depth + 1
                    queue.append((neighbor, depth + 1))
                
                edge_data = G.get_edge_data(curr, neighbor)
                visited_edges.append({
                    "id": edge_data.get("id"),
                    "source": curr,
                    "target": neighbor,
                    "relation": edge_data.get("relation"),
                    "confidence": edge_data.get("confidence", 1.0)
                })

        node_list = []
        for nid, dep in visited_nodes.items():
            nd = G.nodes[nid]
            node_list.append({
                "id": nid,
                "label": nd.get("label"),
                "type": nd.get("type"),
                "depth": dep,
                "properties": nd.get("properties")
            })

        explain_paths = []
        for edge in visited_edges:
            src_lbl = G.nodes[edge["source"]].get("label")
            tgt_lbl = G.nodes[edge["target"]].get("label")
            rel = edge["relation"]
            conf = edge["confidence"]
            explain_paths.append(
                f"Entity '{src_lbl}' is connected to '{tgt_lbl}' via relationship '{rel}' (Confidence: {int(conf * 100)}%)"
            )

        return {
            "nodes": node_list,
            "edges": visited_edges,
            "explainability": explain_paths
        }

    def dfs_traversal(
        self, 
        start_node_id: str, 
        max_depth: int = 2, 
        document_version_id: uuid.UUID | None = None
    ) -> Dict[str, Any]:
        """Depth First Search traversal tracing deep semantic references."""
        G = self.load_networkx_graph(document_version_id)
        if G is None or start_node_id not in G:
            return {"nodes": [], "edges": [], "explainability": []}

        visited_nodes = {}
        visited_edges = []

        def dfs(curr: str, depth: int):
            if depth > max_depth:
                return
            if curr not in visited_nodes or visited_nodes[curr] > depth:
                visited_nodes[curr] = depth

            for neighbor in G.successors(curr):
                if neighbor not in visited_nodes:
                    visited_edges.append({
                        "id": G[curr][neighbor].get("id"),
                        "source": curr,
                        "target": neighbor,
                        "relation": G[curr][neighbor].get("relation"),
                        "confidence": G[curr][neighbor].get("confidence", 1.0)
                    })
                    dfs(neighbor, depth + 1)

        dfs(start_node_id, 0)

        node_list = []
        for nid, dep in visited_nodes.items():
            nd = G.nodes[nid]
            node_list.append({
                "id": nid,
                "label": nd.get("label"),
                "type": nd.get("type"),
                "depth": dep,
                "properties": nd.get("properties")
            })

        explain_paths = []
        for edge in visited_edges:
            src_lbl = G.nodes[edge["source"]].get("label")
            tgt_lbl = G.nodes[edge["target"]].get("label")
            rel = edge["relation"]
            conf = edge["confidence"]
            explain_paths.append(
                f"Entity '{src_lbl}' depends on/relates to '{tgt_lbl}' via '{rel}' (Confidence: {int(conf * 100)}%)"
            )

        return {
            "nodes": node_list,
            "edges": visited_edges,
            "explainability": explain_paths
        }

    def personalized_pagerank(
        self, 
        query_node_labels: List[str], 
        document_version_id: uuid.UUID | None = None
    ) -> List[Dict[str, Any]]:
        """Computes PageRank centered around seed entity labels for semantic prioritization."""
        G = self.load_networkx_graph(document_version_id)
        if G is None or len(G.nodes) == 0:
            return []

        personalization = {}
        matched_node_ids = []
        
        for nid, data in G.nodes(data=True):
            lbl = str(data.get("label", "")).lower()
            if any(q.lower() in lbl for q in query_node_labels):
                matched_node_ids.append(nid)
                personalization[nid] = 1.0
            else:
                personalization[nid] = 0.0

        if sum(personalization.values()) == 0.0:
            for nid in G.nodes:
                personalization[nid] = 1.0 / len(G.nodes)

        total = sum(personalization.values())
        for k in personalization:
            personalization[k] /= total

        try:
            pr = nx.pagerank(G, personalization=personalization, alpha=0.85, max_iter=100)
            sorted_nodes = sorted(pr.items(), key=lambda x: x[1], reverse=True)
            
            results = []
            for nid, score in sorted_nodes[:15]:
                nd = G.nodes[nid]
                results.append({
                    "id": nid,
                    "label": nd.get("label"),
                    "type": nd.get("type"),
                    "pagerank_score": round(score, 6),
                    "properties": nd.get("properties")
                })
            return results
        except Exception:
            deg = nx.degree_centrality(G)
            sorted_nodes = sorted(deg.items(), key=lambda x: x[1], reverse=True)
            return [
                {
                    "id": nid,
                    "label": G.nodes[nid].get("label"),
                    "type": G.nodes[nid].get("type"),
                    "pagerank_score": round(score, 6),
                    "properties": G.nodes[nid].get("properties")
                }
                for nid, score in sorted_nodes[:15]
            ]
