"""RAG Orchestration Engine."""
from typing import Dict, Any
from sqlalchemy.orm import Session
from services.legal_ai.qa import DocumentQAEngine

class LegalRAGEngine:
    def __init__(self, db: Session, kb_version: str = "v1.0.0"):
        self.db = db
        self.qa_engine = DocumentQAEngine(db, kb_version=kb_version)

    def answer_query(self, document_id: str, query: str) -> Dict[str, Any]:
        """Orchestrate RAG flow for document Q&A."""
        return self.qa_engine.answer_question(document_id, query)
