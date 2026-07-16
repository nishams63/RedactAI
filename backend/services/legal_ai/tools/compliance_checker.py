from services.legal_ai.tools.base import BaseTool
from typing import Dict, Any

class ComplianceCheckerTool(BaseTool):
    @property
    def name(self) -> str:
        return "compliance_checker"

    @property
    def description(self) -> str:
        return "Evaluates whether a clause complies with statutory obligations (DPDP Act, RBI Guidelines) and maps violations."

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "clause_text": {"type": "string", "description": "The contract clause text to verify compliance for."},
                "regulations": {"type": "string", "description": "Relevant regulations to compare against, e.g. DPDP, RBI."}
            },
            "required": ["clause_text"]
        }

    def run(self, arguments: Dict[str, Any], context_metadata: Dict[str, Any]) -> Dict[str, Any]:
        from services.legal_ai.slm import LocalSLMInferenceEngine
        slm = LocalSLMInferenceEngine()
        
        clause_text = arguments.get("clause_text")
        regulations = arguments.get("regulations", "DPDP Act 2023 and RBI guidelines")
        
        system_prompt = f"You are a legal compliance auditor. Evaluate the user's clause text against the following regulations: {regulations}. Identify any gaps, compliance scores (0-100), and recommended revisions."
        user_prompt = f"Clause text: {clause_text}"
        
        slm_result = slm.generate_response(system_prompt, user_prompt)
        
        return {
            "audit_report": slm_result["text"],
            "model_used": slm_result["reasoning_engine"],
            "inference_time_ms": slm_result["inference_time_ms"]
        }
