from typing import Dict, Any
from sqlalchemy.orm import Session
from models.document import Document
from services.legal_ai.retriever import LegalRetriever
from services.legal_ai.slm import LocalSLMInferenceEngine
from services.legal_ai.citations import LegalCitationValidator
from services.legal_ai.prompts import PromptRegistryManager
from services.legal_ai.explanations import PrivacyExplanationEngine
from services.legal_ai.compliance import ComplianceCheckEngine

class DocumentQAEngine:
    def __init__(self, db: Session, kb_version: str = "v1.0.0"):
        self.db = db
        self.retriever = LegalRetriever(kb_version=kb_version)
        self.slm_engine = LocalSLMInferenceEngine()
        self.citation_validator = LegalCitationValidator()
        self.explanation_engine = PrivacyExplanationEngine()
        self.compliance_engine = ComplianceCheckEngine()
        self.prompt_manager = PromptRegistryManager(db)

    def answer_question(self, document_id: str, question: str) -> Dict[str, Any]:
        """Query document context and legal regulations to generate RAG response with calibrated confidence."""
        if not document_id or document_id in ["null", "undefined", "None", ""]:
            return {"error": "Please upload and select a legal document context first."}
        try:
            import uuid
            uuid.UUID(str(document_id))
        except ValueError:
            return {"error": "Invalid document ID format."}

        doc = self.db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            return {"error": "Selected document context was not found."}

        # Combine text content from document
        document_text = ""
        if hasattr(doc, "pages") and doc.pages:
            document_text = "\n".join([p.text for p in doc.pages if p.text])
        if not document_text:
            document_text = doc.title or "General Contract"

        # 1. Retrieve relevant legal sections from Vector store
        retrieved = self.retriever.retrieve(f"{question} (context: {doc.title})", top_k=4)
        retrieved_chunks = [item[0] for item in retrieved]
        retrieved_scores = [item[1] for item in retrieved]

        # 2. Build RAG prompt context
        context_str = ""
        for idx, chunk in enumerate(retrieved_chunks):
            meta = chunk["metadata"]
            context_str += f"[{meta['source']}, Section {meta['section_number']}] (Relevance Score: {round(retrieved_scores[idx], 2)})\n{chunk['text']}\n\n"

        if not context_str:
            context_str = "[Regulatory Guideline, General] Compliance with DPDP notice rules is mandatory."

        # 3. Load active template from versioned prompt registry and build prompts
        rag_template = self.prompt_manager.get_active_prompt("rag_qa_template")
        system_prompt = rag_template.format(context=context_str, question=question)
        user_prompt = f"Analyze document context: {document_text[:1500]}\nAnswer question: {question}"

        # 4. Request SLM response
        slm_result = self.slm_engine.generate_response(system_prompt, user_prompt)
        answer = slm_result["text"]

        # 5. Extract and validate citations
        citation_details = self.citation_validator.validate_and_score_citations(answer, retrieved_chunks)

        # 6. Calibrate confidence score
        # Confidence incorporates:
        #  - mean retrieval similarity score (60% weight)
        #  - citation correctness rate (30% weight)
        #  - citation coverage rate (10% weight)
        mean_retrieval = sum(retrieved_scores) / len(retrieved_scores) if retrieved_scores else 0.5
        correctness = citation_details["citation_correctness"]
        coverage = citation_details["citation_coverage"]
        
        raw_confidence = (mean_retrieval * 0.60) + (correctness * 0.30) + (coverage * 0.10)
        
        # Penalize if unsupported claims or hallucinations detected
        if citation_details["unsupported_claims_count"] > 0:
            raw_confidence = max(0.20, raw_confidence - 0.25)
            
        confidence_score = round(max(0.0, min(0.98, raw_confidence)), 2)

        # Calibrated Confidence Reason
        if confidence_score >= 0.85:
            confidence_reason = "High confidence: Response is strongly supported by validated context citations and matches the retrieved regulations."
        elif confidence_score >= 0.65:
            confidence_reason = "Medium confidence: Supported by retrieved context, but with partial citation coverage or moderate retrieval scores."
        else:
            reasons = []
            if citation_details["unsupported_claims_count"] > 0:
                reasons.append("unsupported claims or potential hallucinations detected")
            if mean_retrieval < 0.5:
                reasons.append("low relevance of retrieved context chunks")
            if coverage < 0.3:
                reasons.append("low citation coverage")
            reason_str = ", ".join(reasons) if reasons else "weak alignment between generated text and reference sections"
            confidence_reason = f"Low confidence: Review recommended due to: {reason_str}."

        # Supporting regulations listing
        supporting_regulations = [
            f"{c['metadata']['source']} Section {c['metadata']['section_number']}: {c['metadata']['title']}"
            for c in retrieved_chunks
        ]

        return {
            "answer": answer,
            "confidence_score": confidence_score,
            "confidence_reason": confidence_reason,
            "citations": citation_details["citations"],
            "citation_coverage": citation_details["citation_coverage"],
            "citation_correctness": citation_details["citation_correctness"],
            "unsupported_claims_count": citation_details["unsupported_claims_count"],
            "warning": citation_details["warning"],
            "human_review_recommended": citation_details["human_review_recommended"],
            
            # Explainability details
            "reasoning_engine": slm_result["reasoning_engine"],
            "evidence": context_str,
            "retrieved_clauses": [c["text"] for c in retrieved_chunks],
            "supporting_regulations": list(set(supporting_regulations)),
            "confidence_explanation": (
                f"Calibrated from mean retrieval score ({round(mean_retrieval, 2)}), "
                f"citation correctness ({round(correctness, 2)}), and coverage ({round(coverage, 2)}). "
                f"Penalty of -0.25 applied for {citation_details['unsupported_claims_count']} unsupported claim(s)."
                if citation_details["unsupported_claims_count"] > 0 else
                f"Calibrated from mean retrieval score ({round(mean_retrieval, 2)}), "
                f"citation correctness ({round(correctness, 2)}), and coverage ({round(coverage, 2)})."
            ),
            "inference_time_ms": slm_result["inference_time_ms"]
        }
