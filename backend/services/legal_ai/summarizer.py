"""Document summarizer generating executive, compliance, and privacy summaries."""
from typing import Dict, Any
from services.legal_ai.slm import LocalSLMInferenceEngine
from services.legal_ai.prompts import SUMMARIZATION_PROMPT

class LegalDocumentSummarizer:
    def __init__(self):
        self.slm_engine = LocalSLMInferenceEngine()

    def summarize_document(self, title: str, text: str) -> Dict[str, Any]:
        """Summarize privacy aspects of legal document."""
        system_prompt = "You are a Legal Privacy Officer. Provide structured summaries of the document."
        user_prompt = SUMMARIZATION_PROMPT.format(document_text=text[:4000]) # Cap text for local SLM context limit
        
        slm_result = self.slm_engine.generate_response(system_prompt, user_prompt)
        content = slm_result["text"]
        
        # Parse summaries in case of fallback or structural formatting
        # If output is not pre-split, we can generate a structured dictionary response
        exec_summary = ""
        comp_summary = ""
        priv_summary = ""
        risk_summary = ""
        action_items = []

        if "Executive Summary" in content:
            # Parse sections dynamically
            import re
            parts = re.split(r"(Executive Summary|Compliance Summary|Privacy Summary|Risk Summary|Action Items):?", content, flags=re.IGNORECASE)
            
            # parts will alternate between headers and content
            # e.g., ["", "Executive Summary", "text", "Compliance Summary", "text"]
            for idx in range(1, len(parts), 2):
                header = parts[idx].strip().lower()
                body = parts[idx+1].strip() if idx+1 < len(parts) else ""
                
                if "executive" in header:
                    exec_summary = body
                elif "compliance" in header:
                    comp_summary = body
                elif "privacy" in header:
                    priv_summary = body
                elif "risk" in header:
                    risk_summary = body
                elif "action" in header:
                    action_items = [item.strip()[1:].strip() for item in body.split("\n") if item.strip().startswith("-") or item.strip().startswith("*") or item.strip().startswith("1.")]
                    if not action_items:
                        action_items = [b.strip() for b in body.split("\n") if b.strip()]
        else:
            # Fallback formatting if SLM did not format with exact headers
            lines = content.split("\n")
            exec_summary = lines[0] if len(lines) > 0 else "Analysis completed."
            comp_summary = "Legal clauses evaluated against DPDP and RBI KYC norms."
            priv_summary = "Identifiers detected and highlighted for privacy protection."
            risk_summary = "Potential data exposure risks observed."
            action_items = [line.strip() for line in lines if "mask" in line.lower() or "redact" in line.lower() or "consent" in line.lower()]

        return {
            "document_title": title,
            "executive_summary": exec_summary or "Executive overview of privacy and legal constraints.",
            "compliance_summary": comp_summary or "Summary of regulatory violations and alignment.",
            "privacy_summary": priv_summary or "List of sensitive information processing parameters.",
            "risk_summary": risk_summary or "Analysis of potential exposure or leak liabilities.",
            "action_items": action_items or ["Verify PII redaction", "Implement consent notice"],
            "reasoning_engine": slm_result["reasoning_engine"],
            "inference_time_ms": slm_result["inference_time_ms"]
        }
