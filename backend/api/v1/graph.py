from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
import uuid

from dependencies import get_db, get_current_user
from models.user import User
from models.graph import GraphNode, GraphEdge
from models.document import Document, DocumentVersion
from services.legal_ai.graph_traversal import KnowledgeGraphTraversalEngine
from services.legal_ai.graph_analytics import KnowledgeGraphAnalytics
from services.legal_ai.graph_observability import KnowledgeGraphObservability

router = APIRouter(prefix="/graph", tags=["Knowledge Graph"])

@router.get("/entities")
def get_graph_entities(
    document_version_id: Optional[str] = Query(None),
    node_type: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Paginated list of nodes in the organization's knowledge graph."""
    query = db.query(GraphNode).filter(GraphNode.organization_id == current_user.organization_id)
    
    if document_version_id:
        try:
            ver_uuid = uuid.UUID(document_version_id)
            query = query.filter(GraphNode.document_version_id == ver_uuid)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid document_version_id UUID")
            
    if node_type:
        query = query.filter(GraphNode.node_type == node_type)
        
    total = query.count()
    nodes = query.order_by(GraphNode.created_at.desc()).offset(offset).limit(limit).all()
    
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "nodes": [
            {
                "id": str(n.id),
                "node_type": n.node_type,
                "label": n.label,
                "properties": n.properties,
                "created_at": n.created_at.isoformat()
            }
            for n in nodes
        ]
    }


@router.get("/entity/{id}")
def get_graph_entity_details(
    id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Detailed metadata and properties of a specific graph node."""
    try:
        node_uuid = uuid.UUID(id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid node UUID format")
        
    node = db.query(GraphNode).filter(
        GraphNode.id == node_uuid,
        GraphNode.organization_id == current_user.organization_id
    ).first()
    
    if not node:
        raise HTTPException(status_code=404, detail="Graph node not found")
        
    return {
        "id": str(node.id),
        "node_type": node.node_type,
        "label": node.label,
        "properties": node.properties,
        "created_at": node.created_at.isoformat()
    }


@router.get("/relationships")
def get_graph_relationships(
    document_version_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Paginated list of edges in the organization's knowledge graph."""
    query = db.query(GraphEdge).filter(GraphEdge.organization_id == current_user.organization_id)
    
    if document_version_id:
        try:
            ver_uuid = uuid.UUID(document_version_id)
            query = query.filter(GraphEdge.document_version_id == ver_uuid)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid document_version_id UUID")
            
    total = query.count()
    edges = query.order_by(GraphEdge.created_at.desc()).offset(offset).limit(limit).all()
    
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "edges": [
            {
                "id": str(e.id),
                "source_node_id": str(e.source_node_id),
                "target_node_id": str(e.target_node_id),
                "relationship_type": e.relationship_type,
                "weight": e.weight,
                "confidence_score": e.confidence_score,
                "verification_status": e.verification_status,
                "properties": e.properties
            }
            for e in edges
        ]
    }


@router.get("/document/{id}")
def get_document_subgraph(
    id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Fetch subgraph nodes and edges associated with a specific document (latest version)."""
    try:
        doc_uuid = uuid.UUID(id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid document UUID")
        
    doc = db.query(Document).filter(
        Document.id == doc_uuid,
        Document.organization_id == current_user.organization_id
    ).first()
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    latest_version = db.query(DocumentVersion).filter(
        DocumentVersion.document_id == doc_uuid
    ).order_by(DocumentVersion.created_at.desc()).first()
    
    if not latest_version:
        return {"nodes": [], "edges": [], "document_version_id": None}
        
    nodes = db.query(GraphNode).filter(
        GraphNode.document_version_id == latest_version.id,
        GraphNode.organization_id == current_user.organization_id
    ).all()
    
    edges = db.query(GraphEdge).filter(
        GraphEdge.document_version_id == latest_version.id,
        GraphEdge.organization_id == current_user.organization_id
    ).all()
    
    return {
        "document_version_id": str(latest_version.id),
        "version_number": latest_version.version_number,
        "nodes": [
            {"id": str(n.id), "label": n.label, "type": n.node_type, "properties": n.properties}
            for n in nodes
        ],
        "edges": [
            {
                "id": str(e.id),
                "source": str(e.source_node_id),
                "target": str(e.target_node_id),
                "relation": e.relationship_type,
                "weight": e.weight,
                "confidence": e.confidence_score,
                "properties": e.properties
            }
            for e in edges
        ]
    }


@router.post("/query")
def query_graph_nodes(
    payload: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Search for graph nodes by keyword matching properties."""
    text_query = payload.get("query", "")
    node_type = payload.get("node_type")
    
    query = db.query(GraphNode).filter(
        GraphNode.organization_id == current_user.organization_id,
        GraphNode.label.like(f"%{text_query}%")
    )
    
    if node_type:
        query = query.filter(GraphNode.node_type == node_type)
        
    nodes = query.limit(20).all()
    return {
        "results": [
            {
                "id": str(n.id),
                "label": n.label,
                "type": n.node_type,
                "properties": n.properties
            }
            for n in nodes
        ]
    }


@router.post("/traverse")
def traverse_graph_paths(
    payload: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Runs traversal (BFS/DFS/PPR) from a start node to gather pathways and paths explanation."""
    start_node_id = payload.get("start_node_id")
    method = payload.get("method", "bfs")
    max_depth = payload.get("max_depth", 2)
    document_version_id = payload.get("document_version_id")

    if not start_node_id and method != "pagerank":
        raise HTTPException(status_code=400, detail="start_node_id is required for BFS/DFS traversal")

    engine = KnowledgeGraphTraversalEngine(db, current_user.organization_id)
    ver_uuid = uuid.UUID(document_version_id) if document_version_id else None

    if method == "dfs":
        return engine.dfs_traversal(start_node_id, max_depth, ver_uuid)
    elif method == "pagerank":
        query_labels = payload.get("query_labels", [])
        return {
            "nodes": engine.personalized_pagerank(query_labels, ver_uuid),
            "edges": [],
            "explainability": ["Personalized PageRank run completed."]
        }
    else:
        return engine.bfs_traversal(start_node_id, max_depth, ver_uuid)


@router.get("/statistics")
def get_graph_analytics_and_observability(
    document_version_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Computes global and per-version observability metrics, community partitions, and hubs."""
    ver_uuid = uuid.UUID(document_version_id) if document_version_id else None
    
    analytics = KnowledgeGraphAnalytics(db, current_user.organization_id)
    observability = KnowledgeGraphObservability(db, current_user.organization_id)
    
    return {
        "observability": observability.get_metrics(ver_uuid),
        "analytics": analytics.compute_analytics(ver_uuid)
    }
