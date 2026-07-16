import uuid
import pytest
from sqlalchemy.orm import Session
from database.session import SessionLocal, Base, engine

# Force all database tables to exist before tests execute
Base.metadata.create_all(bind=engine)

from models.user import User
from models.organization import Organization
from models.document import Document, DocumentVersion
from models.document_intelligence import DocumentPage, DocumentEntity
from models.graph import GraphNode, GraphEdge
from services.legal_ai.graph_builder import KnowledgeGraphBuilder
from services.legal_ai.graph_traversal import KnowledgeGraphTraversalEngine
from services.legal_ai.graph_analytics import KnowledgeGraphAnalytics
from services.legal_ai.graph_observability import KnowledgeGraphObservability

def get_test_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def setup_test_context(db: Session):
    org1 = db.query(Organization).filter(Organization.name == "Graph Org 1").first()
    if not org1:
        org1 = Organization(name="Graph Org 1")
        db.add(org1)
        db.commit()
        db.refresh(org1)
        
    org2 = db.query(Organization).filter(Organization.name == "Graph Org 2").first()
    if not org2:
        org2 = Organization(name="Graph Org 2")
        db.add(org2)
        db.commit()
        db.refresh(org2)

    # Setup User
    user = db.query(User).filter(User.email == "graph_test@example.com").first()
    if not user:
        user = User(
            email="graph_test@example.com",
            hashed_password="hashed",
            full_name="Graph Tester",
            organization_id=org1.id,
            is_active=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    # Setup Document & Version
    doc = db.query(Document).filter(Document.title == "Test Graph Contract").first()
    if not doc:
        doc = Document(
            title="Test Graph Contract",
            original_filename="graph.pdf",
            mime_type="application/pdf",
            owner_id=user.id,
            organization_id=org1.id,
            storage_path="s3://test/graph.pdf",
            file_size=1024
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)

    doc_version = db.query(DocumentVersion).filter(DocumentVersion.document_id == doc.id).first()
    if not doc_version:
        doc_version = DocumentVersion(
            document_id=doc.id,
            version_number=1,
            storage_path=doc.storage_path,
            file_size=doc.file_size
        )
        db.add(doc_version)
        db.commit()
        db.refresh(doc_version)

    page1 = db.query(DocumentPage).filter(DocumentPage.document_id == doc.id, DocumentPage.page_number == 1).first()
    if not page1:
        page1 = DocumentPage(
            document_id=doc.id,
            page_number=1,
            text="This Agreement is entered into between Acme Corporation and John Doe. Acme Corporation resides in California."
        )
        db.add(page1)
        db.commit()

    # Add dummy entities
    ent1 = db.query(DocumentEntity).filter(DocumentEntity.document_id == doc.id, DocumentEntity.value == "Acme Corporation").first()
    if not ent1:
        db.add(DocumentEntity(
            document_id=doc.id,
            page_number=1,
            entity_type="ORGANIZATION",
            value="Acme Corporation",
            confidence=0.95,
            start_char=41,
            end_char=57,
            risk_level="LOW"
        ))
    ent2 = db.query(DocumentEntity).filter(DocumentEntity.document_id == doc.id, DocumentEntity.value == "John Doe").first()
    if not ent2:
        db.add(DocumentEntity(
            document_id=doc.id,
            page_number=1,
            entity_type="PERSON",
            value="John Doe",
            confidence=0.98,
            start_char=62,
            end_char=70,
            risk_level="LOW"
        ))
    db.commit()
    
    return org1, org2, user, doc, doc_version

def test_graph_builder_and_provenance():
    db = next(get_test_db())
    org1, org2, user, doc, doc_version = setup_test_context(db)

    # 1. Run Graph Builder
    nodes_created = KnowledgeGraphBuilder.build_graph_for_document(db, doc_version.id)
    assert nodes_created > 0

    # 2. Verify Nodes created
    nodes = db.query(GraphNode).filter(GraphNode.document_version_id == doc_version.id).all()
    assert len(nodes) > 0
    
    types = [n.node_type for n in nodes]
    assert "Document" in types
    assert "Paragraph" in types

    acme_node = next(n for n in nodes if "Acme" in n.label)
    assert acme_node.properties["originating_document_id"] == str(doc.id)
    assert acme_node.properties["page_number"] == 1
    assert acme_node.properties["extraction_model"] == "LegalBERT + EntityLinker"

    # 3. Verify Edges created
    edges = db.query(GraphEdge).filter(GraphEdge.document_version_id == doc_version.id).all()
    assert len(edges) > 0
    assert edges[0].verification_status == "PENDING"
    assert edges[0].confidence_score > 0.0

def test_graph_traversal_bfs_dfs_ppr():
    db = next(get_test_db())
    org1, org2, user, doc, doc_version = setup_test_context(db)
    
    nodes = db.query(GraphNode).filter(GraphNode.document_version_id == doc_version.id).all()
    acme_node = next(n for n in nodes if "Acme" in n.label)

    engine = KnowledgeGraphTraversalEngine(db, org1.id)

    # 1. Run BFS
    bfs_res = engine.bfs_traversal(str(acme_node.id), max_depth=2)
    assert len(bfs_res["nodes"]) > 0
    assert len(bfs_res["explainability"]) > 0
    assert any("Acme" in msg for msg in bfs_res["explainability"])

    # 2. Run DFS
    dfs_res = engine.dfs_traversal(str(acme_node.id), max_depth=2)
    assert len(dfs_res["nodes"]) > 0
    assert len(dfs_res["explainability"]) > 0

    # 3. Run Personalized PageRank
    ppr_res = engine.personalized_pagerank(["Acme"])
    assert len(ppr_res) > 0
    assert "Acme" in ppr_res[0]["label"]

def test_graph_analytics_and_observability():
    db = next(get_test_db())
    org1, org2, user, doc, doc_version = setup_test_context(db)

    # 1. Test Observability
    obs = KnowledgeGraphObservability(db, org1.id)
    metrics = obs.get_metrics(doc_version.id)
    assert metrics["node_count"] > 0
    assert metrics["edge_count"] > 0
    assert metrics["density"] >= 0.0

    # 2. Test Analytics
    analytics = KnowledgeGraphAnalytics(db, org1.id)
    results = analytics.compute_analytics(doc_version.id)
    assert "communities" in results
    assert "hubs" in results
    assert "betweenness_centrality" in results

def test_graph_multi_tenant_isolation():
    db = next(get_test_db())
    org1, org2, user, doc, doc_version = setup_test_context(db)

    engine_org2 = KnowledgeGraphTraversalEngine(db, org2.id)
    G = engine_org2.load_networkx_graph(doc_version.id)
    
    assert len(G.nodes) == 0
    assert len(G.edges) == 0
