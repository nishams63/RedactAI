from services.legal_ai.tools.base import BaseTool
from typing import Dict, Any

class TimelineExtractorTool(BaseTool):
    @property
    def name(self) -> str:
        return "timeline_extractor"

    @property
    def description(self) -> str:
        return "Extracts key dates, milestones, and temporal obligations chronologically from contract texts."

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "context": {"type": "string", "description": "The contract text to extract dates from."}
            },
            "required": ["context"]
        }

    def run(self, arguments: Dict[str, Any], context_metadata: Dict[str, Any]) -> Dict[str, Any]:
        from services.legal_ai.slm import LocalSLMInferenceEngine
        slm = LocalSLMInferenceEngine()
        context_text = arguments.get("context")
        
        system_prompt = "You are a legal timeline extractor. Identify all dates, deadlines, milestones, and durations in the text and present them in chronological order as a bulleted timeline."
        user_prompt = f"Extract timeline from text:\n{context_text}"
        
        slm_result = slm.generate_response(system_prompt, user_prompt)
        
        return {
            "timeline": slm_result["text"],
            "model_used": slm_result["reasoning_engine"],
            "inference_time_ms": slm_result["inference_time_ms"]
        }
