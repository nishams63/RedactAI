from services.legal_ai.tools.base import BaseTool
from typing import Dict, Any

class ContractSummarizerTool(BaseTool):
    @property
    def name(self) -> str:
        return "contract_summarizer"

    @property
    def description(self) -> str:
        return "Generates structured summaries, extracting metadata and overview points from contract texts."

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "context": {"type": "string", "description": "The contract text to summarize."}
            },
            "required": ["context"]
        }

    def run(self, arguments: Dict[str, Any], context_metadata: Dict[str, Any]) -> Dict[str, Any]:
        from services.legal_ai.slm import LocalSLMInferenceEngine
        slm = LocalSLMInferenceEngine()
        
        context_text = arguments.get("context")
        
        system_prompt = "You are a legal summarizer. Summarize this document. Focus on key agreements, dates, parties, and scope."
        user_prompt = f"Summarize the following text:\n{context_text}"
        
        slm_result = slm.generate_response(system_prompt, user_prompt)
        
        return {
            "summary": slm_result["text"],
            "model_used": slm_result["reasoning_engine"],
            "inference_time_ms": slm_result["inference_time_ms"]
        }
