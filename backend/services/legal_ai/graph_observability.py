import uuid
import networkx as nx
from typing import Dict, Any
from sqlalchemy.orm import Session
from services.legal_ai.graph_traversal import KnowledgeGraphTraversalEngine

class KnowledgeGraphObservability:
    def __init__(self, db: Session, organization_id: uuid.UUID):
        self.db = db
        self.org_id = organization_id
        self.engine = KnowledgeGraphTraversalEngine(db, organization_id)

    def get_metrics(self, document_version_id: uuid.UUID | None = None) -> Dict[str, Any]:
        """Calculates graph structural metrics for dashboard reporting."""
        G = self.engine.load_networkx_graph(document_version_id)
        
        node_count = len(G.nodes)
        edge_count = len(G.edges)
        
        if node_count == 0:
            return {
                "node_count": 0,
                "edge_count": 0,
                "density": 0.0,
                "isolated_nodes_count": 0,
                "avg_degree": 0.0,
                "largest_component_size": 0,
                "diameter": 0
            }

        density = nx.density(G)
        isolated = list(nx.isolates(G))
        isolated_count = len(isolated)

        degrees = [val for _, val in G.degree()]
        avg_degree = sum(degrees) / len(degrees) if degrees else 0.0

        try:
            undirected_G = G.to_undirected()
            components = list(nx.connected_components(undirected_G))
            largest_comp = max(components, key=len) if components else set()
            largest_size = len(largest_comp)
            
            sub_G = undirected_G.subgraph(largest_comp)
            diameter = nx.diameter(sub_G) if len(largest_comp) > 1 else 0
        except Exception:
            largest_size = 0
            diameter = 0

        return {
            "node_count": node_count,
            "edge_count": edge_count,
            "density": round(density, 4),
            "isolated_nodes_count": isolated_count,
            "avg_degree": round(avg_degree, 2),
            "largest_component_size": largest_size,
            "diameter": diameter
        }
