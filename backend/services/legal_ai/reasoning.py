"""Legal clause parser and privacy risk reasoning engine."""
import re
from typing import List, Dict, Any

class LegalReasoningEngine:
    def __init__(self):
        # Keywords for classifying legal clauses
        self.clause_rules = [
            {
                "type": "Confidentiality & Non-Disclosure",
                "pattern": r"confidential|disclosure|secret|proprietary|non-disclosure|nda",
                "risk": "HIGH",
                "impact": "High Privacy Impact",
                "rec": "Ensure clear definitions of confidential data, exclude public information, and specify termination terms."
            },
            {
                "type": "Data Protection & Processing",
                "pattern": r"personal data|pii|privacy|processing|gdpr|dpdp|controller|fiduciary|consent",
                "risk": "HIGH",
                "impact": "Critical Privacy Impact",
                "rec": "Require explicit consent notices, minimize data elements collected, and enforce deletion procedures."
            },
            {
                "type": "Limitation of Liability",
                "pattern": r"liability|indemnify|hold harmless|damages|maximum|negligence",
                "risk": "MEDIUM",
                "impact": "Medium Legal Impact",
                "rec": "Audit indemnification caps for data security breaches and third-party liabilities."
            },
            {
                "type": "Intellectual Property",
                "pattern": r"intellectual property|patent|copyright|trademark|invention|ownership",
                "risk": "MEDIUM",
                "impact": "Low Privacy Impact",
                "rec": "Confirm clear assignment of IP and ownership rules for custom software or deliverables."
            },
            {
                "type": "Governing Law & Dispute Resolution",
                "pattern": r"governing law|dispute|arbitration|jurisdiction|courts",
                "risk": "LOW",
                "impact": "Low Legal Impact",
                "rec": "Ensure dispute resolution venue aligns with company location."
            }
        ]

    def split_into_clauses(self, text: str) -> List[str]:
        """Split document text into distinct clauses by section numbers, numbered lists, or newlines."""
        # Split by typical list items or headers e.g. "Section 1", "1.", "\n\n"
        raw_clauses = re.split(r'(?=\n\d+\.|\nSection|\nArticle|\n[A-Z][a-z]+ Agreement)', text)
        if len(raw_clauses) <= 1:
            raw_clauses = [p.strip() for p in text.split("\n\n") if p.strip()]
        
        # Clean clauses
        clauses = []
        for c in raw_clauses:
            cleaned = c.strip()
            if len(cleaned) > 20:  # Filter out header snippets
                clauses.append(cleaned)
        
        # Fallback if text is small
        if not clauses:
            clauses = [text]
        return clauses

    def analyze_clause(self, clause_text: str) -> Dict[str, Any]:
        """Classify clause, detect sensitive terms, risk levels, and actions."""
        clause_type = "General Provisions / Miscellaneous"
        risk_level = "LOW"
        privacy_impact = "Low Privacy Impact"
        recommendation = "Review for standard business compatibility."
        
        # Detect classification matches
        lower_clause = clause_text.lower()
        for rule in self.clause_rules:
            if re.search(rule["pattern"], lower_clause):
                clause_type = rule["type"]
                risk_level = rule["risk"]
                privacy_impact = rule["impact"]
                recommendation = rule["rec"]
                break

        # Check for sensitive indicators
        sensitive_data = []
        if re.search(r"aadhaar|\b\d{4}\b", lower_clause):
            sensitive_data.append("Aadhaar Number")
            risk_level = "HIGH"
        if re.search(r"pan card|\b[A-Z]{5}\d{4}[A-Z]\b", lower_clause):
            sensitive_data.append("PAN Card Number")
            risk_level = "HIGH"
        if re.search(r"phone|mobile|\+91", lower_clause):
            sensitive_data.append("Phone Number")
        if re.search(r"email|contact", lower_clause):
            sensitive_data.append("Email Address")
        if re.search(r"bank|account|credit card", lower_clause):
            sensitive_data.append("Financial Account Details")
            risk_level = "HIGH"

        return {
            "clause_text": clause_text,
            "clause_type": clause_type,
            "sensitive_data": sensitive_data,
            "risk_level": risk_level,
            "privacy_impact": privacy_impact,
            "recommended_action": recommendation
        }

    def analyze_document_clauses(self, text: str) -> List[Dict[str, Any]]:
        clauses = self.split_into_clauses(text)
        return [self.analyze_clause(c) for c in clauses]
