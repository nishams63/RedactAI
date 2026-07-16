import os
import uuid
import pytest
from sqlalchemy.orm import Session
from database.session import SessionLocal, Base, engine

# Ensure all database tables exist before tests execute
Base.metadata.create_all(bind=engine)

# Imports from RAG components
from models.rag import RAGChunk, RAGEmbedding, RAGSearchAnalytics
from services.legal_ai.chunker import LegalDocumentChunker
from services.legal_ai.embeddings.factory import EmbeddingProviderFactory
from services.legal_ai.retrieval.vector import VectorRetrievalStrategy
from services.legal_ai.retrieval.bm25 import BM25RetrievalStrategy
from services.legal_ai.retrieval.rrf import ReciprocalRankFusion
from services.legal_ai.retrieval.reranker import CrossEncoderReranker
from services.legal_ai.retrieval_pipeline import LegalRetrievalPipeline
from services.legal_ai.citation_engine import LegalCitationEngine
from services.legal_ai.answer_generator import LegalAnswerGenerator
from services.legal_ai.query_processor import LegalQueryProcessor

MOCK_TEXT = """This Agreement is entered into on 2026-07-16.

Section 1. Confidentiality Obligations
The receiving party shall keep all personal data secure and comply with privacy rules.

Section 2. Retention Periods
The data fiduciary shall not store data longer than 3 years.
(a) Notice must be sent to UIDAI within 48 hours of any breach.
(b) Masking must be applied to all customer onboarding Aadhaar records."""


def test_1_document_chunker():
    """Verify paragraph, clause, section and sliding-window chunking outputs."""
    chunker = LegalDocumentChunker()
    meta = {"title": "Test NDA Agreement.pdf", "page_number": 1}

    # Paragraph chunking
    p_chunks = chunker.chunk_by_paragraphs(MOCK_TEXT, meta)
    assert len(p_chunks) >= 2
    assert p_chunks[0]["chunk_type"] == "paragraph"
    assert "Context: [Document: Test NDA Agreement.pdf]" in p_chunks[0]["text"]

    # Clause chunking
    c_chunks = chunker.chunk_by_clauses(MOCK_TEXT, meta)
    assert len(c_chunks) >= 2
    assert c_chunks[1]["chunk_type"] == "clause"

    # Section chunking
    s_chunks = chunker.chunk_by_sections(MOCK_TEXT, meta)
    assert len(s_chunks) >= 2
    assert s_chunks[0]["chunk_type"] == "section"

    # Sliding window chunking
    sw_chunks = chunker.chunk_sliding_window(MOCK_TEXT, chunk_size_words=20, overlap_words=5, doc_metadata=meta)
    assert len(sw_chunks) >= 1
    assert sw_chunks[0]["chunk_type"] == "sliding_window"


def test_2_embedding_providers():
    """Verify that MiniLM, LegalBERT, and BGE providers conform to dimension interfaces."""
    for model_name, expected_dim in [("MiniLM", 384), ("LegalBERT", 768), ("BGE", 384)]:
        provider = EmbeddingProviderFactory.get_provider(model_name)
        assert provider.dimension == expected_dim
        
        emb = provider.get_embedding("Test regulatory clause text")
        assert len(emb) == expected_dim
        
        embs = provider.get_embeddings(["First text", "Second text"])
        assert len(embs) == 2
        assert len(embs[0]) == expected_dim


def test_3_query_preprocessor():
    """Verify query cleaning, intent classification, expansion, and metadata filter extraction."""
    processor = LegalQueryProcessor()
    raw_query = "What is the penalty for non-compliance under RBI in 2026 for client C123?"
    
    result = processor.process_query(raw_query)
    
    assert result["cleaned_query"] != ""
    assert result["intent_classification"] == "compliance"
    assert "penalty" in result["expanded_query"]
    
    filters = result["extracted_metadata_filters"]
    assert filters["year"] == 2026
    assert filters["client"] == "C123"


def test_4_retrieval_strategies():
    """Verify RRF merging and cross-encoder jaccard-based semantic reranker."""
    # 1. Test Reciprocal Rank Fusion
    v_results = [
        ({"chunk_id": "c1", "text": "Confidentiality clause details"}, 0.9),
        ({"chunk_id": "c2", "text": "Retention period details"}, 0.8)
    ]
    b_results = [
        ({"chunk_id": "c2", "text": "Retention period details"}, 1.5),
        ({"chunk_id": "c3", "text": "UIDAI breach notification details"}, 1.0)
    ]
    
    fused = ReciprocalRankFusion.fuse(v_results, b_results, top_n=2)
    assert len(fused) == 2
    # c2 should rank highest as it is in both lists
    assert fused[0][0]["chunk_id"] == "c2"

    # 2. Test CrossEncoderReranker proxy
    reranker = CrossEncoderReranker()
    query = "UIDAI breach notification"
    candidates = [
        ({"chunk_id": "c1", "text": "Confidentiality clause details"}, 0.5),
        ({"chunk_id": "c3", "text": "UIDAI breach notification details"}, 0.4)
    ]
    
    reranked = reranker.rerank(query, candidates)
    # c3 has higher term overlap (UIDAI, breach, notification) so it should rank highest
    assert reranked[0][0]["chunk_id"] == "c3"


def test_5_citation_engine():
    """Verify citation extraction and validation matching."""
    engine = LegalCitationEngine()
    
    answer_text = "As stated in [UIDAI Circular, Page 1] and [DPDP Act 2023, Page 2], breach notifications are required."
    retrieved_context = [
        {
            "chunk_id": "c1",
            "text": "UIDAI notification guidelines",
            "metadata": {
                "document_title": "UIDAI Circular",
                "page_number": 1,
                "chunk_type": "paragraph"
            }
        },
        {
            "chunk_id": "c2",
            "text": "DPDP rules",
            "metadata": {
                "document_title": "DPDP Act 2023",
                "page_number": 2,
                "chunk_type": "paragraph"
            }
        }
    ]
    
    validation_res = engine.validate_and_score(answer_text, retrieved_context)
    
    assert len(validation_res["citations"]) == 2
    assert validation_res["citation_correctness"] == 1.0
    assert validation_res["unsupported_claims_count"] == 0
    assert validation_res["human_review_recommended"] is False
