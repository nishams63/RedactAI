import os
import jinja2
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from services.legal_ai.slm import LocalSLMInferenceEngine
from services.legal_ai.citation_engine import LegalCitationEngine

class LegalAnswerGenerator:
    """Generates grounded, citation-backed answers utilizing Jinja templates and local SLM inference."""
    def __init__(self, db_session: Session):
        self.db = db_session
        self.slm_engine = LocalSLMInferenceEngine()
        self.citation_engine = LegalCitationEngine()
        
        # Setup Jinja file template loader
        current_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.template_dir = os.path.join(current_dir, "prompts")
        self.jinja_env = jinja2.Environment(loader=jinja2.FileSystemLoader(self.template_dir))

    def _render_prompt(self, template_name: str, context: Dict[str, Any]) -> str:
        """Loads and renders a versioned Jinja template from disk."""
        try:
            template = self.jinja_env.get_template(template_name)
            return template.render(**context)
        except Exception as e:
            # Safe basic string fallback
            print(f"Jinja template render failed: {e}. Running string fallback.")
            if "grounded_answer" in template_name:
                return f"Context:\n{context.get('context')}\n\nQuestion:\n{context.get('question')}"
            return str(context)

    def generate_grounded_answer(
        self, 
        query: str, 
        retrieved_context: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Queries the local SLM using the grounded prompt, validates citations, and calibrates confidence."""
        # 1. Format the context string
        context_str = ""
        for idx, chunk in enumerate(retrieved_context):
            meta = chunk.get("metadata", {})
            context_str += f"[{meta.get('document_title')}, Page {meta.get('page_number')}] (Relevance: {round(chunk.get('score', 0.95), 2)})\n{chunk['text']}\n\n"
            
        if not context_str:
            context_str = "[Context] No specific regulatory context was found."

        # 2. Render prompt from Jinja file
        system_prompt = self._render_prompt(
            "grounded_answer.jinja",
            {"context": context_str, "question": query}
        )
        user_prompt = f"Answer query: {query}"

        # 3. Call local Qwen SLM inference engine
        slm_result = self.slm_engine.generate_response(system_prompt, user_prompt)
        answer = slm_result["text"]

        # 4. Extract and validate citations
        citation_details = self.citation_engine.validate_and_score(answer, retrieved_context)

        # 5. Calibrate confidence score
        retrieval_scores = [c.get("score", 0.95) for c in retrieved_context]
        mean_retrieval = sum(retrieval_scores) / len(retrieval_scores) if retrieval_scores else 0.5
        correctness = citation_details["citation_correctness"]
        coverage = citation_details["citation_coverage"]
        
        raw_confidence = (mean_retrieval * 0.60) + (correctness * 0.30) + (coverage * 0.10)
        if citation_details["unsupported_claims_count"] > 0:
            raw_confidence = max(0.20, raw_confidence - 0.25)
            
        confidence_score = round(max(0.0, min(0.98, raw_confidence)), 2)

        # Confidence Reason
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
            
            # Metadata stats
            "reasoning_engine": slm_result["reasoning_engine"],
            "evidence": context_str,
            "inference_time_ms": slm_result["inference_time_ms"]
        }
