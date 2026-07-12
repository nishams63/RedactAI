"""Regulatory compliance check engine."""
from typing import List, Dict, Any
from services.legal_ai.reasoning import LegalReasoningEngine

class ComplianceCheckEngine:
    def __init__(self):
        self.reasoning_engine = LegalReasoningEngine()

    def evaluate_compliance(self, document_text: str) -> Dict[str, Any]:
        """Verify document clauses against DPDP and corporate privacy policies."""
        clauses = self.reasoning_engine.analyze_document_clauses(document_text)
        
        score = 100
        violations = []
        risk_categories = {
            "Data Protection Violations": "LOW",
            "Sensitive Data Risks": "LOW",
            "Contractual Pitfalls": "LOW"
        }
        
        # Check rule 1: Consent notice presence
        has_consent = any("consent" in c["clause_text"].lower() or "notice" in c["clause_text"].lower() for c in clauses)
        if not has_consent:
            score -= 20
            violations.append({
                "rule": "DPDP Section 5: Notice Requirement",
                "severity": "HIGH",
                "issue": "No explicit consent notice or processing disclosures found in the document.",
                "remedy": "Add a dedicated clause notifying parties how their personal data is collected and processed."
            })
            risk_categories["Data Protection Violations"] = "HIGH"

        # Check rule 2: Personal data storage masking
        has_pii = any(len(c["sensitive_data"]) > 0 for c in clauses)
        has_masking = any("mask" in c["clause_text"].lower() or "redact" in c["clause_text"].lower() for c in clauses)
        if has_pii and not has_masking:
            score -= 15
            violations.append({
                "rule": "UIDAI Aadhaar Storage Rule / DPDP Section 4",
                "severity": "HIGH",
                "issue": "PII elements detected (e.g. Identity Cards/Financial numbers) without accompanying masking rules.",
                "remedy": "Integrate a mandate to mask identity card files (like Aadhaar and PAN) before archiving."
            })
            risk_categories["Sensitive Data Risks"] = "HIGH"

        # Check rule 3: Retention policy (minimization)
        has_retention = any("retain" in c["clause_text"].lower() or "delete" in c["clause_text"].lower() or "purge" in c["clause_text"].lower() for c in clauses)
        if not has_retention:
            score -= 15
            violations.append({
                "rule": "Company Privacy Policy Rule 15: PII Minimization",
                "severity": "MEDIUM",
                "issue": "No explicit data retention limit or deletion instructions found.",
                "remedy": "Add clause limiting customer PII retention to 180 days post service contract termination."
            })
            if risk_categories["Data Protection Violations"] != "HIGH":
                risk_categories["Data Protection Violations"] = "MEDIUM"

        # Ensure score stays in bounds
        score = max(10, score)
        
        # Determine overall rating
        if score >= 85:
            rating = "FULLY COMPLIANT"
        elif score >= 70:
            rating = "PARTIALLY COMPLIANT"
        else:
            rating = "NON-COMPLIANT"

        required_actions = [v["remedy"] for v in violations]
        
        return {
            "compliance_score": score,
            "compliance_status": rating,
            "detected_violations": violations,
            "risk_categories": risk_categories,
            "required_actions": required_actions,
            "clauses_evaluated_count": len(clauses)
        }
