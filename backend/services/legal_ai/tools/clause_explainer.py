from services.legal_ai.tools.base import BaseTool
from typing import Dict, Any

class ClauseExplainerTool(BaseTool):
    @property
    def name(self) -> str:
        return "clause_explainer"

    @property
    def description(self) -> str:
        return "Explains legal clauses, translated into plain-language business terms, with rights and warnings."

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "clause": {"type": "string", "description": "The specific clause text to explain."},
                "context": {"type": "string", "description": "Surrounding section details (optional)."}
            },
            "required": ["clause"]
        }

    def run(self, arguments: Dict[str, Any], context_metadata: Dict[str, Any]) -> Dict[str, Any]:
        from services.legal_ai.slm import LocalSLMInferenceEngine
        slm = LocalSLMInferenceEngine()
        
        clause = arguments.get("clause")
        context_str = arguments.get("context", "")
        
        from services.legal_ai.prompt_manager import PromptManager
        pm = PromptManager()
        system_prompt = pm.render("clause_explainer.jinja", {"clause": clause, "context": context_str})
        user_prompt = f"Explain the clause: {clause}"
        
        slm_result = slm.generate_response(system_prompt, user_prompt)
        
        return {
            "explanation": slm_result["text"],
            "model_used": slm_result["reasoning_engine"],
            "inference_time_ms": slm_result["inference_time_ms"]
        }
