"""Integration and unit tests for the 10 NLP Extension Modules."""
import uuid
import pytest
from fastapi.testclient import TestClient

from main import app
from database.session import SessionLocal
from models.user import User
from models.document import Document
from models.document_intelligence import DocumentPage, DocumentBlock, DocumentEntity

# Import services
from services.ai.preprocessor import preprocessor
from services.ai.structure_analyzer import structure_analyzer
from services.ai.clause_classifier import clause_classifier
from services.ai.relation_extractor import relation_extractor
from services.ai.entity_linker import entity_linker
from services.ai.semantic_search import semantic_search_engine
from services.ai.duplicate_detector import duplicate_detector
from services.ai.keyword_extractor import keyword_extractor

client = TestClient(app)

# Mock data
MOCK_LEGAL_TEXT = (
    "This NON-DISCLOSURE AGREEMENT (the \"Agreement\") is made u/s 4 of the Companies Act, 2013 "
    "between TCS Ltd. (having its registered office at Mumbai) and Amit Sharma residing at Pune, India. "
    "The Disclosing Party agrees to share certain proprietary and confidential trade secrets. "
    "Either party may terminate this agreement upon 30 days notice. Governing Law is the law of Delhi. "
    "All disputes shall be resolved by arbitration in Mumbai."
)

def test_module_1_preprocessor():
    """Test unicode normalization, noise correction, abbreviation expansion, language detection, and tokenization/syntax analysis."""
    # Abbreviation expansion
    expanded = preprocessor.expand_abbreviations("This is u/s 4 of IPC vs. State.")
    assert "under section" in expanded
    assert "Indian Penal Code" in expanded
    assert "versus" in expanded

    # OCR noise correction
    cleaned = preprocessor.correct_ocr_noise("agree-\nment with stray | character")
    assert "agreement" in cleaned
    assert "|" not in cleaned

    # Unicode normalization
    norm = preprocessor.normalize_unicode("T\u00e9st")
    assert norm == "Tést"

    # Full preprocessor pipeline run
    res = preprocessor.preprocess(MOCK_LEGAL_TEXT)
    assert res["language"] == "English"
    assert "benchmarks" in res
    assert "character" in res["benchmarks"]
    assert "word" in res["benchmarks"]
    assert len(res["sentences"]) > 0

def test_module_2_structure_analyzer():
    """Test classification of layout blocks into legal categories (Title, Header, Section, etc.)."""
    title_block = structure_analyzer.classify_block(
        "NON-DISCLOSURE AGREEMENT", page_num=1, coords=[100, 40, 400, 80], page_height=842.0
    )
    assert title_block == "Title"

    header_block = structure_analyzer.classify_block(
        "Page 1 of 5", page_num=1, coords=[100, 20, 200, 30], page_height=842.0
    )
    assert header_block == "Header"

    sig_block = structure_analyzer.classify_block(
        "Signed, sealed and delivered by Authorized Signatory", page_num=2, coords=[100, 700, 300, 750], page_height=842.0
    )
    assert sig_block == "Signature Area"

    list_block = structure_analyzer.classify_block(
        "1. First obligation item", page_num=2, coords=[100, 200, 400, 230], page_height=842.0
    )
    assert list_block == "List"

def test_module_3_clause_classifier():
    """Test legal clause classification accuracy and confidence scoring."""
    conf_clause = "The Receiving Party shall keep all Disclosing Party secrets confidential and private."
    res_conf = clause_classifier.classify_clause(conf_clause)
    assert res_conf["clause_type"] in ["Confidentiality", "Non-Disclosure", "Privacy"]
    assert res_conf["confidence"] > 0.3

    gov_clause = "This contract shall be interpreted and governed under the laws of Delhi, India."
    res_gov = clause_classifier.classify_clause(gov_clause)
    assert res_gov["clause_type"] == "Governing Law"
    assert res_gov["confidence"] > 0.5

def test_module_4_relation_extractor():
    """Test extraction of relationships between entities (Person-Org, Org-Address, etc.)."""
    entities = [
        {"entity_type": "PERSON", "value": "Amit Sharma", "start_char": 100, "end_char": 111},
        {"entity_type": "ORGANIZATION", "value": "TCS Ltd.", "start_char": 50, "end_char": 58},
        {"entity_type": "ADDRESS", "value": "Mumbai, India", "start_char": 70, "end_char": 83}
    ]
    clauses = [{"clause_type": "Confidentiality", "risk_level": "HIGH"}]
    
    res = relation_extractor.extract_relations(MOCK_LEGAL_TEXT, entities, clauses=clauses)
    assert "nodes" in res
    assert "edges" in res
    
    # Check node types
    node_types = {n["type"] for n in res["nodes"]}
    assert "PERSON" in node_types
    assert "ORGANIZATION" in node_types
    assert "ADDRESS" in node_types
    assert "CONTRACT" in node_types
    assert "CLAUSE" in node_types

def test_module_5_entity_linker():
    """Test alias resolution and canonical duplicate entity grouping."""
    entities = [
        {"entity_type": "ORGANIZATION", "value": "TCS Ltd.", "page_number": 1},
        {"entity_type": "ORGANIZATION", "value": "Tata Consultancy Services", "page_number": 2},
        {"entity_type": "ORGANIZATION", "value": "TCS", "page_number": 3},
        {"entity_type": "PERSON", "value": "Amit Sharma", "page_number": 1},
        {"entity_type": "PERSON", "value": "Mr. Amit Sharma", "page_number": 2}
    ]
    
    linked = entity_linker.link_entities(entities)
    # Validate grouping
    org_groups = [g for g in linked if g["entity_type"] == "ORGANIZATION"]
    person_groups = [g for g in linked if g["entity_type"] == "PERSON"]
    
    # "TCS Ltd", "TCS", "Tata Consultancy Services" should link together
    assert len(org_groups) >= 1
    assert any("Tata Consultancy Services" in g["canonical_name"] or "TCS" in g["canonical_name"] for g in org_groups)

    # "Amit Sharma" and "Mr. Amit Sharma" should link together
    assert len(person_groups) == 1
    assert "Amit Sharma" in person_groups[0]["canonical_name"]

def test_module_6_semantic_search():
    """Test indexing and local semantic search querying."""
    doc_id = uuid.uuid4()
    org_id = uuid.uuid4()
    blocks = [
        {"page_number": 1, "block_type": "Section", "text": "This clause governs governing laws and court jurisdiction in Mumbai."},
        {"page_number": 1, "block_type": "Paragraph", "text": "The price for services is one thousand dollars paid via invoice invoice invoices."}
    ]
    
    # Index document blocks
    indexed = semantic_search_engine.index_document(doc_id, org_id, blocks)
    assert indexed is True

    # Search within document
    results = semantic_search_engine.search_document(doc_id, "courts and jurisdiction rules", top_k=1)
    assert len(results) > 0
    assert "governs governing laws" in results[0]["text"]

    # Global organization search
    results_global = semantic_search_engine.search_organization(org_id, "invoices and service prices", top_k=1)
    assert len(results_global) > 0
    assert "invoice" in results_global[0]["text"]

def test_module_7_duplicate_detector():
    """Test duplicate clause and near-duplicate document checks."""
    blocks = [
        {"page_number": 1, "block_type": "Paragraph", "text": "This is a strictly confidential non-disclosure clause guarding trade secrets."},
        {"page_number": 2, "block_type": "Paragraph", "text": "This is a strictly confidential non-disclosure clause guarding trade secrets."}, # Exact copy
        {"page_number": 3, "block_type": "Paragraph", "text": "The service fee is due monthly after invoice generation in cash."}
    ]
    
    duplicates = duplicate_detector.find_duplicate_clauses(blocks)
    assert len(duplicates) > 0
    assert duplicates[0]["similarity_score"] > 0.95

def test_module_8_keyword_extractor():
    """Test legal terms, risk/compliance keywords, and summary generation."""
    res = keyword_extractor.extract_keywords(MOCK_LEGAL_TEXT)
    assert "top_keywords" in res
    assert "legal_terms" in res
    assert "risk_keywords" in res
    assert "compliance_keywords" in res
    assert "summary" in res
    
    # Check that key terms are extracted
    legal_words = {item["word"] for item in res["legal_terms"]}
    assert "confidentiality" in legal_words or "arbitration" in legal_words


def test_nlp_api_endpoints():
    """Test all NLP REST API endpoints under /api/v1/nlp."""
    db = SessionLocal()
    # Create unique test email to avoid collisions
    email = f"nlp_tester_{uuid.uuid4().hex[:6]}@example.com"
    
    # 1. Register
    reg_resp = client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "TestPassword123!",
        "full_name": "NLP Tester",
        "organization_name": "NLP Test Corp"
    })
    assert reg_resp.status_code == 201
    token = reg_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Get current user and org from DB to seed a document
    user = db.query(User).filter(User.email == email).first()
    assert user is not None
    
    # Create document
    doc_id = uuid.uuid4()
    doc = Document(
        id=doc_id,
        title="Test NLP Contract",
        original_filename="contract.pdf",
        storage_path=f"local://uploads/{doc_id}/contract.pdf",
        file_size=len(MOCK_LEGAL_TEXT),
        mime_type="application/pdf",
        owner_id=user.id,
        organization_id=user.organization_id,
        status="Processed"
    )
    db.add(doc)
    db.commit()
    
    # Seed document page and blocks
    page = DocumentPage(
        id=uuid.uuid4(),
        document_id=doc_id,
        page_number=1,
        text=MOCK_LEGAL_TEXT
    )
    db.add(page)
    
    block = DocumentBlock(
        id=uuid.uuid4(),
        document_id=doc_id,
        page_number=1,
        block_type="Paragraph",
        text=MOCK_LEGAL_TEXT,
        coordinates=[10, 10, 100, 100],
        reading_order=1
    )
    db.add(block)
    
    entity = DocumentEntity(
        id=uuid.uuid4(),
        document_id=doc_id,
        page_number=1,
        entity_type="ORGANIZATION",
        value="TCS Ltd.",
        confidence=0.95,
        start_char=50,
        end_char=58,
        bounding_box=[10, 10, 100, 100],
        risk_level="LOW"
    )
    db.add(entity)
    db.commit()
    
    # Index document blocks in semantic search engine
    semantic_search_engine.index_document(doc_id, user.organization_id, [{
        "page_number": 1,
        "block_type": "Paragraph",
        "text": MOCK_LEGAL_TEXT,
        "coordinates": [10, 10, 100, 100],
        "reading_order": 1
    }])

    # 2. Test GET /nlp/analytics
    resp = client.get("/api/v1/nlp/analytics", headers=headers)
    assert resp.status_code == 200
    assert "clause_distribution" in resp.json()

    # 3. Test GET /nlp/{document_id}/preprocessed
    resp = client.get(f"/api/v1/nlp/{doc_id}/preprocessed", headers=headers)
    assert resp.status_code == 200
    assert "benchmarks" in resp.json()

    # 4. Test GET /nlp/{document_id}/clauses
    resp = client.get(f"/api/v1/nlp/{doc_id}/clauses", headers=headers)
    assert resp.status_code == 200
    assert "clauses" in resp.json()

    # 5. Test GET /nlp/{document_id}/relations
    resp = client.get(f"/api/v1/nlp/{doc_id}/relations", headers=headers)
    assert resp.status_code == 200
    assert "nodes" in resp.json()

    # 6. Test GET /nlp/{document_id}/entity-graph
    resp = client.get(f"/api/v1/nlp/{doc_id}/entity-graph", headers=headers)
    assert resp.status_code == 200
    assert "linked_entities" in resp.json()

    # 7. Test POST /nlp/{document_id}/semantic-search
    resp = client.post(f"/api/v1/nlp/{doc_id}/semantic-search", json={"query": "secrets disclosure", "top_k": 2}, headers=headers)
    assert resp.status_code == 200
    assert "results" in resp.json()

    # 8. Test POST /nlp/semantic-search
    resp = client.post("/api/v1/nlp/semantic-search", json={"query": "disputes resolution", "top_k": 2}, headers=headers)
    assert resp.status_code == 200
    assert "results" in resp.json()

    # 9. Test GET /nlp/{document_id}/duplicates
    resp = client.get(f"/api/v1/nlp/{doc_id}/duplicates", headers=headers)
    assert resp.status_code == 200
    assert "duplicate_clauses" in resp.json()

    # 10. Test GET /nlp/{document_id}/keywords
    resp = client.get(f"/api/v1/nlp/{doc_id}/keywords", headers=headers)
    assert resp.status_code == 200
    assert "legal_terms" in resp.json()

    # 11. Test GET /nlp/{document_id}/explain
    resp = client.get(f"/api/v1/nlp/{doc_id}/explain", headers=headers)
    assert resp.status_code == 200
    assert "explanations" in resp.json()

    # Clean up DB
    from models.user import RefreshToken
    db.query(RefreshToken).filter(RefreshToken.user_id == user.id).delete()
    db.delete(entity)
    db.delete(block)
    db.delete(page)
    db.delete(doc)
    db.delete(user)
    db.commit()
    db.close()
