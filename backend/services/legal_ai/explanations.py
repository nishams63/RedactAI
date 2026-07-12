"""Legal privacy explanation engine for detected entities."""
from typing import List, Dict, Any

class PrivacyExplanationEngine:
    def __init__(self):
        self.entity_map = {
            "AADHAAR": {
                "reason": "Unique 12-digit Indian national identity number issued by UIDAI.",
                "sensitivity": "Highly Sensitive Personal Data (identity theft, fraud, and profiling risks).",
                "regulation": "UIDAI Storage and Masking Guidelines (Section 3.2) & DPDP Act 2023.",
                "risk_level": "CRITICAL",
                "recommendation": "Mask the first 8 digits (e.g. ****-****-1234) before sharing or storing outside secure vaults."
            },
            "PAN": {
                "reason": "Permanent Account Number issued by the Income Tax Department.",
                "sensitivity": "Financial Information (linked to banking, taxation, and asset profiling).",
                "regulation": "RBI KYC Guidelines & IT Act 2000 (Section 43A).",
                "risk_level": "HIGH",
                "recommendation": "Redact or encrypt PAN identifiers in transaction logs and service records."
            },
            "EMAIL": {
                "reason": "Electronic mail address.",
                "sensitivity": "Personal Contact Information (phishing, spam, and unauthorized tracking).",
                "regulation": "DPDP Act 2023 (Section 4 - Consent requirements).",
                "risk_level": "MEDIUM",
                "recommendation": "Partially redact (e.g., u***@domain.com) or obtain explicit consent for communication."
            },
            "PHONE": {
                "reason": "Mobile or telephone contact number.",
                "sensitivity": "Personal Contact Information (unauthorized profiling, marketing, and spoofing).",
                "regulation": "DPDP Act 2023 & Telecom Regulatory Authority of India (TRAI) privacy directives.",
                "risk_level": "HIGH",
                "recommendation": "Mask middle 6 digits (e.g., +91-XXXXXX-1234) or restrict access to customer agents."
            },
            "BANK_ACCOUNT": {
                "reason": "Financial bank account or transaction reference number.",
                "sensitivity": "Highly Sensitive Financial Information (financial theft and compliance breaches).",
                "regulation": "RBI KYC Guidelines & IT Act 2000 Section 43A.",
                "risk_level": "CRITICAL",
                "recommendation": "Redact account numbers completely or expose only the last 4 digits."
            },
            "IFSC": {
                "reason": "Indian Financial System Code representing a specific bank branch.",
                "sensitivity": "Linked Financial Metadata.",
                "regulation": "RBI Banking Privacy Regulations.",
                "risk_level": "MEDIUM",
                "recommendation": "Mask or redact if paired with a bank account number."
            },
            "PASSPORT": {
                "reason": "National travel and citizenship document.",
                "sensitivity": "Highly Sensitive Personal Identification.",
                "regulation": "DPDP Act 2023 & RBI KYC Guidelines.",
                "risk_level": "CRITICAL",
                "recommendation": "Mask photo, passport number, and signature before archiving."
            },
            "VOTER_ID": {
                "reason": "Elector's Photo Identity Card issued by the Election Commission of India.",
                "sensitivity": "National Identification Document.",
                "regulation": "DPDP Act 2023.",
                "risk_level": "HIGH",
                "recommendation": "Mask identifier code in records."
            }
        }

    def explain_entity(self, entity_type: str, text: str) -> Dict[str, Any]:
        """Generate legal explanation and recommended actions for a detected entity."""
        upper_type = entity_type.upper()
        if upper_type in self.entity_map:
            details = self.entity_map[upper_type]
        else:
            details = {
                "reason": "Generic personal data identifier.",
                "sensitivity": "Personal Data (unauthorized disclosure risk).",
                "regulation": "DPDP Act 2023 (Section 4).",
                "risk_level": "LOW",
                "recommendation": "Review storage access permissions and mask if not functionally necessary."
            }

        return {
            "entity_type": entity_type,
            "detected_text": text,
            "reason": details["reason"],
            "sensitivity": details["sensitivity"],
            "applicable_law": details["regulation"],
            "risk_level": details["risk_level"],
            "recommendation": details["recommendation"]
        }

    def explain_all_entities(self, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [
            self.explain_entity(entity.get("entity_type"), entity.get("text"))
            for entity in entities
        ]
