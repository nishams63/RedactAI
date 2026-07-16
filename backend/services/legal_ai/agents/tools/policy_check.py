import re
from typing import Dict, Any
from services.legal_ai.agents.tools.base import BaseTool
from services.legal_ai.agents.context import SharedContext

class PolicyCheckerTool(BaseTool):
    @property
    def tool_id(self) -> str:
        return "policy_checker"

    def execute(self, inputs: Dict[str, Any], context: SharedContext) -> Dict[str, Any]:
        """Validates contract text compliance against GDPR, DPDP, HIPAA, and RBI guidelines."""
        text_content = inputs.get("text", "")
        if not text_content and context.retrieved_chunks:
            text_content = " ".join([c.get("text", "") for c in context.retrieved_chunks])

        results = {
            "GDPR": {
                "checked": True,
                "matches": re.findall(r"GDPR|personal\s+data|data\s+subject|data\s+processor|consent\s+withdrawal", text_content, re.IGNORECASE),
            },
            "DPDP": {
                "checked": True,
                "matches": re.findall(r"DPDP|data\s+fiduciary|data\s+principal|consent\s+manager|significant\s+data", text_content, re.IGNORECASE),
            },
            "HIPAA": {
                "checked": True,
                "matches": re.findall(r"HIPAA|PHI|protected\s+health|health\s+information|business\s+associate", text_content, re.IGNORECASE),
            },
            "RBI": {
                "checked": True,
                "matches": re.findall(r"RBI|Reserve\s+Bank|outsourcing\s+guidelines|banking\s+secrecy|financial\s+data", text_content, re.IGNORECASE),
            }
        }

        issues = []
        compliant_frameworks = []
        
        for framework, data in results.items():
            found_count = len(data["matches"])
            if found_count > 0:
                compliant_frameworks.append(framework)
            else:
                issues.append(f"No active clause provisions identified for {framework} compliance.")

        is_compliant = len(issues) == 0
        status = "COMPLIANT" if is_compliant else "NON-COMPLIANT"
        if issues and len(compliant_frameworks) > 0:
            status = "PARTIALLY-COMPLIANT"

        return {
            "compliance_status": status,
            "compliant_frameworks": compliant_frameworks,
            "non_compliant_frameworks": [f for f in results.keys() if f not in compliant_frameworks],
            "identified_markers": {f: list(set(data["matches"])) for f, data in results.items()},
            "compliance_gaps": issues
        }
