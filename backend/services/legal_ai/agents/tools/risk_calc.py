import re
from typing import Dict, Any
from services.legal_ai.agents.tools.base import BaseTool
from services.legal_ai.agents.context import SharedContext

class RiskCalculatorTool(BaseTool):
    @property
    def tool_id(self) -> str:
        return "risk_calculator"

    def execute(self, inputs: Dict[str, Any], context: SharedContext) -> Dict[str, Any]:
        """Scrapes text segments for liability indicators and returns exposure index."""
        text_content = inputs.get("text", "")
        if not text_content and context.retrieved_chunks:
            text_content = " ".join([c.get("text", "") for c in context.retrieved_chunks])

        risk_flags = {
            "unlimited_liability": len(re.findall(r"unlimited\s+liability|uncapped\s+liability", text_content, re.IGNORECASE)),
            "indemnity_obligations": len(re.findall(r"indemnify|indemnity|hold\s+harmless", text_content, re.IGNORECASE)),
            "liquidated_damages": len(re.findall(r"liquidated\s+damages|penalty|forfeit", text_content, re.IGNORECASE)),
            "termination_convenience": len(re.findall(r"termination\s+for\s+convenience|terminate\s+without\s+cause", text_content, re.IGNORECASE)),
        }

        score = sum(count * 20 for count in risk_flags.values())
        exposure_score = min(100.0, float(score))

        severity = "LOW"
        if exposure_score >= 70.0:
            severity = "HIGH"
        elif exposure_score >= 35.0:
            severity = "MEDIUM"

        return {
            "exposure_score": exposure_score,
            "severity_level": severity,
            "risk_counts": risk_flags,
            "reasoning": f"Identified {sum(risk_flags.values())} risky clause markers in active contract segments."
        }
