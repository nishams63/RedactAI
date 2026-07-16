from services.legal_ai.tools.base import BaseTool
from typing import Dict, Any

class RiskAnalyzerTool(BaseTool):
    @property
    def name(self) -> str:
        return "risk_analyzer"

    @property
    def description(self) -> str:
        return "Performs risk explanation, identifying liabilities, exposure, and mitigation strategies."

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "context": {"type": "string", "description": "The contract text to analyze for risk."}
            },
            "required": ["context"]
        }

    def run(self, arguments: Dict[str, Any], context_metadata: Dict[str, Any]) -> Dict[str, Any]:
        from services.legal_ai.slm import LocalSLMInferenceEngine
        slm = LocalSLMInferenceEngine()
        
        context_text = arguments.get("context")
        
        from services.legal_ai.prompt_manager import PromptManager
        pm = PromptManager()
        system_prompt = pm.render("risk_analysis.jinja", {"document_text": context_text})
        user_prompt = "Perform legal risk analysis."
        
        slm_result = slm.generate_response(system_prompt, user_prompt)
        
        return {
            "risk_analysis": slm_result["text"],
            "model_used": slm_result["reasoning_engine"],
            "inference_time_ms": slm_result["inference_time_ms"]
        }
