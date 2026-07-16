from services.legal_ai.tools.base import BaseTool
from typing import Dict, Any, List

class CitationValidatorTool(BaseTool):
    @property
    def name(self) -> str:
        return "citation_validator"

    @property
    def description(self) -> str:
        return "Verifies whether a specific claim or statement can be validated against the retrieved document context."

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "claim": {"type": "string", "description": "The specific claim or statement to validate."},
                "retrieved_context": {"type": "array", "items": {"type": "object"}, "description": "Retrieved context blocks."}
            },
            "required": ["claim", "retrieved_context"]
        }

    def run(self, arguments: Dict[str, Any], context_metadata: Dict[str, Any]) -> Dict[str, Any]:
        from services.legal_ai.citation_engine import LegalCitationEngine
        engine = LegalCitationEngine()
        
        claim = arguments.get("claim")
        retrieved_context = arguments.get("retrieved_context", [])
        
        citation_details = engine.validate_and_score(claim, retrieved_context)
        
        return {
            "is_valid": citation_details["unsupported_claims_count"] == 0,
            "citations": citation_details["citations"],
            "citation_coverage": citation_details["citation_coverage"],
            "citation_correctness": citation_details["citation_correctness"],
            "unsupported_claims_count": citation_details["unsupported_claims_count"],
            "warning": citation_details["warning"]
        }
