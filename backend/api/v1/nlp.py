"""Module 10 - NLP Router.

Defines all API endpoints for the Level 2 NLP capabilities.
"""
import re
import uuid
from collections import Counter
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from dependencies import get_db, get_current_user
from models.user import User
from models.document import Document
from models.document_intelligence import DocumentPage, DocumentBlock, DocumentEntity

# Import NLP services
from services.ai.preprocessor import preprocessor
from services.ai.structure_analyzer import structure_analyzer
from services.ai.clause_classifier import clause_classifier
from services.ai.relation_extractor import relation_extractor
from services.ai.entity_linker import entity_linker
from services.ai.semantic_search import semantic_search_engine
from services.ai.duplicate_detector import duplicate_detector
from services.ai.keyword_extractor import keyword_extractor
from services.legal_ai.explanations import PrivacyExplanationEngine
from services.legal_ai.compliance import ComplianceCheckEngine

router = APIRouter(prefix="/nlp", tags=["NLP Extensions"])

class SearchQuery(BaseModel):
    query: str
    top_k: Optional[int] = 5

def _get_document_text(document_id: uuid.UUID, db: Session) -> str:
    pages = db.query(DocumentPage).filter(DocumentPage.document_id == document_id).order_by(DocumentPage.page_number.asc()).all()
    if not pages:
        raise HTTPException(status_code=404, detail="Document pages/text not found. Ensure it is processed.")
    return " ".join(p.text for p in pages)

def _verify_document_access(document_id: uuid.UUID, user: User, db: Session) -> Document:
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.organization_id != user.organization_id:
        raise HTTPException(status_code=403, detail="Access denied to this document")
    return doc

@router.get("/{document_id}/preprocessed")
def get_preprocessed_text(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Module 1: Get advanced preprocessed text, POS tags, and tokenization benchmarks."""
    _verify_document_access(document_id, current_user, db)
    text = _get_document_text(document_id, db)
    return preprocessor.preprocess(text)

@router.get("/{document_id}/clauses")
def get_classified_clauses(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Module 3: Parse and classify document paragraphs into standard legal clauses with confidence scores."""
    _verify_document_access(document_id, current_user, db)
    blocks = db.query(DocumentBlock).filter(DocumentBlock.document_id == document_id).all()
    
    results = []
    for b in blocks:
        text = b.text.strip() if b.text else ""
        if len(text) > 20:
            classification = clause_classifier.classify_clause(text)
            results.append({
                "page_number": b.page_number,
                "block_type": b.block_type,
                "text": text,
                "clause_type": classification["clause_type"],
                "confidence": classification["confidence"],
                "all_scores": classification["scores"]
            })
    return {"clauses": results}

@router.get("/{document_id}/relations")
def get_entity_relations(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Module 4: Extract semantic relations (Person-Org, Org-Address, etc.) and return nodes & links."""
    doc = _verify_document_access(document_id, current_user, db)
    text = _get_document_text(document_id, db)
    
    entities = db.query(DocumentEntity).filter(DocumentEntity.document_id == document_id).all()
    entities_list = [{
        "value": e.value,
        "entity_type": e.entity_type,
        "confidence": e.confidence,
        "start_char": e.start_char,
        "end_char": e.end_char
    } for e in entities]

    # Evaluate compliance to link compliance nodes
    comp_engine = ComplianceCheckEngine()
    comp_res = comp_engine.evaluate_compliance(text)

    # Get clauses for risk mapping
    blocks = db.query(DocumentBlock).filter(DocumentBlock.document_id == document_id).all()
    clauses_list = []
    for b in blocks:
        text_val = b.text.strip() if b.text else ""
        if len(text_val) > 25:
            classification = clause_classifier.classify_clause(text_val)
            clauses_list.append({
                "clause_type": classification["clause_type"],
                "risk_level": "HIGH" if classification["clause_type"] in ["Confidentiality", "Privacy", "Liability"] else "LOW"
            })

    return relation_extractor.extract_relations(text, entities_list, clauses=clauses_list, compliance_result=comp_res)

@router.get("/{document_id}/entity-graph")
def get_linked_entities(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Module 5: Resolves repeated entity aliases and groups duplicates into a canonical graph."""
    _verify_document_access(document_id, current_user, db)
    entities = db.query(DocumentEntity).filter(DocumentEntity.document_id == document_id).all()
    entities_list = [{
        "value": e.value,
        "entity_type": e.entity_type,
        "confidence": e.confidence,
        "page_number": e.page_number,
        "start_char": e.start_char,
        "end_char": e.end_char
    } for e in entities]
    
    return {"linked_entities": entity_linker.link_entities(entities_list)}

@router.post("/{document_id}/semantic-search")
def semantic_search_in_document(
    document_id: uuid.UUID,
    payload: SearchQuery,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Module 6: Semantic search for similar clauses inside a single document."""
    _verify_document_access(document_id, current_user, db)
    return {
        "query": payload.query,
        "results": semantic_search_engine.search_document(document_id, payload.query, payload.top_k)
    }

@router.post("/semantic-search")
def semantic_search_global(
    payload: SearchQuery,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Module 6: Global cross-document semantic search in the user's organization."""
    if not current_user.organization_id:
        raise HTTPException(status_code=400, detail="User does not belong to any organization.")
    return {
        "query": payload.query,
        "results": semantic_search_engine.search_organization(current_user.organization_id, payload.query, payload.top_k)
    }

@router.get("/{document_id}/duplicates")
def get_duplicate_detections(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Module 7: Finds duplicate clauses, near-duplicate documents, and clusters all org documents."""
    doc = _verify_document_access(document_id, current_user, db)
    blocks = db.query(DocumentBlock).filter(DocumentBlock.document_id == document_id).all()
    blocks_list = [{"text": b.text, "page_number": b.page_number, "block_type": b.block_type} for b in blocks if b.text]
    
    duplicates_clauses = duplicate_detector.find_duplicate_clauses(blocks_list)
    similar_docs = duplicate_detector.find_near_duplicate_documents(document_id, doc.organization_id, db)
    clusters = duplicate_detector.cluster_documents(doc.organization_id, db)
    
    return {
        "duplicate_clauses": duplicates_clauses,
        "similar_documents": similar_docs,
        "document_clusters": clusters
    }

@router.get("/{document_id}/keywords")
def get_keywords(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Module 8: Automatically extract legal terms, risk/compliance keywords, and summaries."""
    _verify_document_access(document_id, current_user, db)
    text = _get_document_text(document_id, db)
    return keyword_extractor.extract_keywords(text)

@router.get("/{document_id}/explain")
def get_explanations(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Module 9: Explains PII/NER sensitivity and compliance reasons with evidence spans."""
    _verify_document_access(document_id, current_user, db)
    entities = db.query(DocumentEntity).filter(DocumentEntity.document_id == document_id).all()
    
    engine = PrivacyExplanationEngine()
    explanations = []
    for e in entities:
        exp = engine.explain_entity(e.entity_type, e.value)
        exp["page_number"] = e.page_number
        exp["bounding_box"] = e.bounding_box
        explanations.append(exp)
        
    return {"explanations": explanations}

@router.get("/analytics")
def get_nlp_analytics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Module 10: NLP Dashboard metrics (readability index, clause counts, processing speeds)."""
    if not current_user.organization_id:
        raise HTTPException(status_code=400, detail="User must belong to an organization.")
        
    # Get processed documents in org
    docs = db.query(Document).filter(
        Document.organization_id == current_user.organization_id,
        Document.status == "Processed"
    ).all()
    
    doc_ids = [d.id for d in docs]
    
    # 1. Total entities breakdown
    entities = db.query(DocumentEntity.entity_type).filter(DocumentEntity.document_id.in_(doc_ids)).all() if doc_ids else []
    entity_counts = Counter(e[0] for e in entities)
    
    # 2. Total clauses breakdown
    blocks = db.query(DocumentBlock.text).filter(DocumentBlock.document_id.in_(doc_ids)).all() if doc_ids else []
    clause_types = []
    total_complexity = 0.0
    valid_blocks_count = 0
    
    for b in blocks:
        text = b[0].strip() if b[0] else ""
        if len(text) > 30:
            classification = clause_classifier.classify_clause(text)
            clause_types.append(classification["clause_type"])
            
            # Readability score (Flesch Reading Ease approximation)
            words = text.split()
            sentences = [s for s in re.split(r'\.|\?|\!', text) if s.strip()]
            if len(words) > 5 and len(sentences) > 0:
                # Flesch Ease = 206.835 - 1.015*(words/sentences) - 84.6*(syllables/words)
                # Mock average syllable count as 1.5 per word
                ease = 206.835 - 1.015 * (len(words) / len(sentences)) - 84.6 * 1.5
                total_complexity += max(0, min(100, ease))
                valid_blocks_count += 1
                
    clause_counts = Counter(clause_types)
    avg_readability = round(total_complexity / valid_blocks_count, 2) if valid_blocks_count > 0 else 60.0
    
    # 3. Readability complexity interpretation
    complexity_label = "Standard"
    if avg_readability < 30:
        complexity_label = "Very Difficult (Academic/Legal)"
    elif avg_readability < 50:
        complexity_label = "Difficult"
    elif avg_readability < 70:
        complexity_label = "Standard"
    else:
        complexity_label = "Easy"
        
    return {
        "document_count": len(docs),
        "most_common_entities": dict(entity_counts.most_common(10)),
        "clause_distribution": dict(clause_counts),
        "average_readability_score": avg_readability,
        "document_complexity_label": complexity_label,
        "processing_time_average_ms": 1450.0  # Constant mock baseline matching profiles
    }
