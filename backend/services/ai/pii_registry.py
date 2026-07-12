"""
PII Registry — Centralized repository of regex patterns for Indian PII.
"""

INDIAN_PII_PATTERNS = {
    "AADHAAR": r"\b\d{4}[\s\n\-]?\d{4}[\s\n\-]?\d{4}\b",
    "PAN": r"\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b",
    "PHONE": r"\b(?:\+91[\-\s]?)?[6789]\d{9}\b",
    "EMAIL": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
    "PASSPORT": r"\b[A-Z][0-9]{7}\b",
    "DRIVING_LICENSE": r"\b[A-Z]{2}-\d{13}\b",
    "VOTER_ID": r"\b[A-Z]{3}[0-9]{7}\b",
    "CREDIT_CARD": r"\b(?:\d[ -]*?){13,16}\b",
    "IFSC": r"\b[A-Z]{4}0[A-Z0-9]{6}\b",
    "UPI_ID": r"\b[a-zA-Z0-9.\-_]+@[a-zA-Z]+\b",
    "PIN_CODE": r"\b\d{6}\b"
}
