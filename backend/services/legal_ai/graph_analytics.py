import uuid
import networkx as nx
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from services.legal_ai.graph_traversal import KnowledgeGraphTraversalEngine

class KnowledgeGraphAnalytics:
    def __init__(self, db: Session, organization_id: uuid.UUID):
        self.db = db
        self.org_id = organization_id
        self.engine = KnowledgeGraphTraversalEngine(db, organization_id)

    def compute_analytics(self, document_version_id: uuid.UUID | None = None) -> Dict[str, Any]:
        """Calculates Louvain communities, PageRanks, centralities, and hubs."""
        G = self.engine.load_networkx_graph(document_version_id)
        if not G or len(G.nodes) == 0:
            return {
                "communities": [],
                "betweenness_centrality": [],
                "closeness_centrality": [],
                "hubs": []
            }

        communities = []
        try:
            undirected_G = G.to_undirected()
            comms = nx.community.louvain_communities(undirected_G)
            for idx, c in enumerate(comms):
                communities.append({
                    "community_id": idx,
                    "node_ids": list(c)
                })
        except Exception:
            comps = list(nx.connected_components(G.to_undirected()))
            for idx, comp in enumerate(comps):
                communities.append({
                    "community_id": idx,
                    "node_ids": list(comp)
                })

        try:
            betweenness = nx.betweenness_centrality(G)
            sorted_between = sorted(betweenness.items(), key=lambda x: x[1], reverse=True)[:10]
        except Exception:
            sorted_between = []

        try:
            closeness = nx.closeness_centrality(G)
            sorted_close = sorted(closeness.items(), key=lambda x: x[1], reverse=True)[:10]
        except Exception:
            sorted_close = []

        degree = nx.degree_centrality(G)
        sorted_degree = sorted(degree.items(), key=lambda x: x[1], reverse=True)[:10]

        hub_nodes = []
        for nid, score in sorted_degree:
            nd = G.nodes[nid]
            hub_nodes.append({
                "id": nid,
                "label": nd.get("label"),
                "type": nd.get("type"),
                "score": round(score, 4)
            })

        return {
            "communities": communities,
            "betweenness_centrality": [
                {"id": nid, "label": G.nodes[nid].get("label"), "score": round(score, 4)}
                for nid, score in sorted_between
            ],
            "closeness_centrality": [
                {"id": nid, "label": G.nodes[nid].get("label"), "score": round(score, 4)}
                for nid, score in sorted_close
            ],
            "hubs": hub_nodes
        }
