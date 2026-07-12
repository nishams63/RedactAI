"""
ML Pipeline Configuration — Level 1 Machine Learning Baseline
Centralizes feature definitions, labeling rules, model hyperparameters,
document type profiles, and versioning constants.
"""
from typing import Dict, List, Any

# ─── Versioning ────────────────────────────────────────────────────────────
GENERATOR_VERSION = "1.0.0"
PREPROCESSING_VERSION = "1.0.0"
FEATURE_SET_VERSION = "1.0.0"
LABELING_RULE_VERSION = "1.0.0"
MODEL_FRAMEWORK = "scikit-learn"
DEFAULT_RANDOM_SEED = 42
DEFAULT_DATASET_SIZE = 5000

# ─── Output Classes ────────────────────────────────────────────────────────
SENSITIVITY_CLASSES = ["Public", "Internal", "Confidential", "Highly Confidential"]

# ─── Feature Definitions ──────────────────────────────────────────────────
BASIC_FEATURES = [
    "num_pages", "total_words", "total_characters", "avg_sentence_length",
]

STRUCTURE_FEATURES = [
    "header_count", "footer_count", "table_count", "image_count",
    "signature_count", "stamp_count",
]

ENTITY_FEATURES = [
    "person_count", "org_count", "location_count", "date_count",
    "money_count", "court_count", "judge_count", "law_count",
    "case_number_count",
]

INDIAN_PII_FEATURES = [
    "aadhaar_count", "pan_count", "passport_count", "driving_license_count",
    "voter_id_count", "email_count", "phone_count", "address_count",
    "bank_account_count", "credit_card_count", "ifsc_count", "upi_count",
]

METADATA_FEATURES = [
    "language_encoded", "is_encrypted", "has_digital_signature",
    "has_producer", "has_author", "document_type_encoded",
]

RISK_FEATURES = [
    "critical_count", "high_count", "medium_count", "low_count",
]

CONFIDENCE_FEATURES = [
    "avg_confidence", "max_confidence",
]

ENGINEERED_FEATURES = [
    "pii_density", "entity_density", "risk_density", "critical_ratio",
    "avg_entities_per_page", "avg_pii_per_page", "doc_length_category",
    "contains_gov_id", "contains_financial_data", "contains_legal_terms",
    "contains_personal_data",
]

ALL_FEATURE_NAMES: List[str] = (
    BASIC_FEATURES + STRUCTURE_FEATURES + ENTITY_FEATURES +
    INDIAN_PII_FEATURES + METADATA_FEATURES + RISK_FEATURES +
    CONFIDENCE_FEATURES + ENGINEERED_FEATURES
)

# ─── Entity Type Mapping ──────────────────────────────────────────────────
ENTITY_TYPE_TO_FEATURE: Dict[str, str] = {
    "PERSON": "person_count",
    "ORGANIZATION": "org_count",
    "LOCATION": "location_count",
    "DATE": "date_count",
    "MONEY": "money_count",
    "COURT": "court_count",
    "JUDGE": "judge_count",
    "LAW": "law_count",
    "CASE_NUMBER": "case_number_count",
    "AADHAAR": "aadhaar_count",
    "PAN": "pan_count",
    "PASSPORT": "passport_count",
    "DRIVING_LICENSE": "driving_license_count",
    "VOTER_ID": "voter_id_count",
    "EMAIL": "email_count",
    "PHONE": "phone_count",
    "ADDRESS": "address_count",
    "BANK_ACCOUNT": "bank_account_count",
    "CREDIT_CARD": "credit_card_count",
    "IFSC": "ifsc_count",
    "UPI_ID": "upi_count",
}

BLOCK_TYPE_TO_FEATURE: Dict[str, str] = {
    "Header": "header_count",
    "Footer": "footer_count",
    "Table": "table_count",
    "Image": "image_count",
    "Signature": "signature_count",
    "Stamp": "stamp_count",
}

RISK_LEVEL_TO_FEATURE: Dict[str, str] = {
    "CRITICAL": "critical_count",
    "HIGH": "high_count",
    "MEDIUM": "medium_count",
    "LOW": "low_count",
}

# ─── Language Encoding ─────────────────────────────────────────────────────
LANGUAGE_ENCODING: Dict[str, int] = {
    "English": 1, "Hindi": 2, "Tamil": 3, "Telugu": 4,
    "Kannada": 5, "Malayalam": 6, "Bengali": 7, "Marathi": 8,
    "Gujarati": 9, "Punjabi": 10, "Urdu": 11, "Unknown": 0,
}

# ─── Document Type Encoding ────────────────────────────────────────────────
DOCUMENT_TYPE_ENCODING: Dict[str, int] = {
    "NDA": 1,
    "Employment Contract": 2,
    "Service Agreement": 3,
    "Invoice": 4,
    "Government Form": 5,
    "Medical Record": 6,
    "Court Order": 7,
    "Passport Copy": 8,
    "Bank Statement": 9,
    "Insurance Document": 10,
    "Property Agreement": 11,
    "Real": 0,
    "Unknown": 0
}

# ─── Deterministic Labeling Rules (Weighted Policy Engine) ─────────────────
def apply_sensitivity_label(features: Dict[str, Any]) -> str:
    """
    Weighted policy engine to assign sensitivity labels.
    Combines: Document Type, Detected PII, Entity Density,
    Financial/Medical Indicators, and Confidence Scores.
    """
    # 1. Document Type Base Score
    doc_type = features.get("document_type", "")
    dt = doc_type.lower()
    
    base_score = 10.0
    if "medical" in dt:
        base_score = 95.0
    elif "passport" in dt:
        base_score = 95.0
    elif "nda" in dt:
        base_score = 30.0
    elif "employment" in dt:
        base_score = 30.0
    elif "government" in dt or "gov_" in dt:
        base_score = 30.0
    elif "service" in dt:
        base_score = 20.0
    elif "invoice" in dt:
        base_score = 20.0
    elif "notice" in dt:
        base_score = 20.0
    elif "statement" in dt or "insurance" in dt:
        base_score = 30.0
    elif "court" in dt:
        base_score = 5.0
        
    score = base_score
    
    # 2. Detected PII Counts
    aadhaar = features.get("aadhaar_count", 0)
    passport = features.get("passport_count", 0)
    bank = features.get("bank_account_count", 0)
    pan = features.get("pan_count", 0)
    dl = features.get("driving_license_count", 0)
    voter = features.get("voter_id_count", 0)
    ifsc = features.get("ifsc_count", 0)
    cc = features.get("credit_card_count", 0)
    upi = features.get("upi_count", 0)
    
    # Critical PII (Aadhaar, Passport, Bank Account)
    critical_pii_score = (aadhaar + passport + bank) * 20.0
    score += critical_pii_score
    
    # High PII (PAN, DL, Voter, IFSC, Credit Card, UPI)
    high_pii_score = (pan + dl + voter + ifsc + cc + upi) * 10.0
    score += high_pii_score
    
    # Medium PII (Phone, Email, Address, PIN)
    phone = features.get("phone_count", 0)
    email = features.get("email_count", 0)
    address = features.get("address_count", 0)
    pin = features.get("pincode_count", 0) or features.get("pin_code", 0) or features.get("pin_code_count", 0)
    medium_pii_score = (phone + email + address + pin) * 3.0
    score += medium_pii_score
    
    # 3. Entity & PII Density
    pii_density = features.get("pii_density", 0.0)
    score += min(pii_density * 2.0, 15.0)
    
    # 4. Financial Information Indicator
    if features.get("contains_financial_data", 0) == 1:
        score += 5.0
        
    # 5. Medical Information Indicator
    if "medical" in dt or features.get("medical_count", 0) > 0:
        score += 10.0
        
    # 6. Confidence Score weight
    avg_conf = features.get("avg_confidence", 1.0)
    score += avg_conf * 5.0
    
    # 7. Document Type specific modifiers
    if "invoice" in dt:
        score -= 55.0
    if "court" in dt:
        score -= 5.0

    # Map score to sensitivity label
    if score >= 108.0:
        return "Highly Confidential"
    elif score >= 40.0:
        return "Confidential"
    elif score >= 15.0:
        return "Internal"
    else:
        return "Public"


# ─── Document Type Profiles ────────────────────────────────────────────────
# Each profile defines mean and std for feature distributions.
# These create statistically realistic synthetic vectors for Indian legal docs.
DOCUMENT_TYPE_PROFILES: Dict[str, Dict[str, Any]] = {
    "NDA": {
        "num_pages": (5, 2), "total_words": (2500, 800),
        "person_count": (4, 2), "org_count": (3, 1), "date_count": (5, 2),
        "email_count": (2, 1), "phone_count": (1, 1), "address_count": (2, 1),
        "pan_count": (0, 0.3), "aadhaar_count": (0, 0.2),
        "signature_count": (2, 1), "stamp_count": (1, 0.5),
        "law_count": (2, 1), "money_count": (1, 1),
        "table_count": (0, 0.3), "header_count": (3, 1), "footer_count": (2, 1),
    },
    "Employment Contract": {
        "num_pages": (8, 3), "total_words": (4000, 1500),
        "person_count": (3, 1), "org_count": (2, 1), "date_count": (8, 3),
        "email_count": (2, 1), "phone_count": (2, 1), "address_count": (3, 1),
        "pan_count": (1, 0.5), "aadhaar_count": (1, 0.5),
        "bank_account_count": (1, 0.5), "ifsc_count": (1, 0.5),
        "signature_count": (2, 1), "stamp_count": (1, 0.5),
        "money_count": (3, 2), "law_count": (1, 1),
        "table_count": (1, 0.5), "header_count": (4, 2), "footer_count": (3, 1),
    },
    "Service Agreement": {
        "num_pages": (10, 4), "total_words": (5000, 2000),
        "person_count": (2, 1), "org_count": (4, 2), "date_count": (6, 3),
        "email_count": (3, 1), "phone_count": (2, 1), "address_count": (3, 1),
        "pan_count": (1, 0.5), "money_count": (5, 3),
        "signature_count": (2, 1), "stamp_count": (1, 0.5),
        "law_count": (3, 2), "table_count": (2, 1),
        "header_count": (5, 2), "footer_count": (3, 1),
    },
    "Court Order": {
        "num_pages": (6, 3), "total_words": (3000, 1200),
        "person_count": (5, 3), "org_count": (2, 1), "date_count": (10, 4),
        "court_count": (3, 1), "judge_count": (2, 1), "case_number_count": (2, 1),
        "law_count": (8, 4), "money_count": (2, 2),
        "address_count": (2, 1), "signature_count": (1, 0.5),
        "header_count": (2, 1), "footer_count": (2, 1),
        "stamp_count": (2, 1),
    },
    "Legal Notice": {
        "num_pages": (3, 1), "total_words": (1500, 600),
        "person_count": (3, 2), "org_count": (2, 1), "date_count": (4, 2),
        "law_count": (4, 2), "court_count": (1, 0.5), "case_number_count": (1, 0.5),
        "email_count": (1, 0.5), "phone_count": (1, 0.5), "address_count": (3, 1),
        "signature_count": (1, 0.5), "stamp_count": (1, 0.5),
        "header_count": (2, 1), "footer_count": (1, 0.5),
    },
    "Invoice": {
        "num_pages": (2, 1), "total_words": (500, 300),
        "person_count": (1, 0.5), "org_count": (2, 1), "date_count": (3, 1),
        "money_count": (5, 3), "bank_account_count": (1, 0.5), "ifsc_count": (1, 0.5),
        "pan_count": (1, 0.5), "email_count": (1, 0.5), "phone_count": (1, 0.5),
        "address_count": (2, 1), "table_count": (2, 1),
        "header_count": (1, 0.5), "footer_count": (1, 0.5),
    },
    "Government Form": {
        "num_pages": (4, 2), "total_words": (1000, 500),
        "person_count": (2, 1), "org_count": (1, 0.5), "date_count": (4, 2),
        "aadhaar_count": (1, 0.5), "pan_count": (1, 0.5), "voter_id_count": (1, 0.5),
        "phone_count": (1, 0.5), "email_count": (1, 0.5), "address_count": (2, 1),
        "signature_count": (1, 0.5), "stamp_count": (2, 1),
        "table_count": (1, 0.5), "header_count": (2, 1), "footer_count": (1, 0.5),
    },
    "Passport Copy": {
        "num_pages": (2, 1), "total_words": (200, 100),
        "person_count": (1, 0.5), "date_count": (3, 1),
        "passport_count": (1, 0.3), "aadhaar_count": (0, 0.3),
        "address_count": (1, 0.5), "image_count": (1, 0.5),
        "signature_count": (1, 0.5),
        "header_count": (1, 0.5), "footer_count": (0, 0.3),
    },
    "Medical Record": {
        "num_pages": (5, 3), "total_words": (2000, 1000),
        "person_count": (3, 1), "org_count": (2, 1), "date_count": (8, 4),
        "aadhaar_count": (1, 0.5), "phone_count": (2, 1), "email_count": (1, 0.5),
        "address_count": (2, 1), "money_count": (2, 1),
        "signature_count": (2, 1), "stamp_count": (1, 0.5),
        "table_count": (2, 1), "header_count": (3, 1), "footer_count": (2, 1),
    },
    "Bank Statement": {
        "num_pages": (6, 3), "total_words": (1500, 800),
        "person_count": (1, 0.5), "org_count": (2, 1), "date_count": (15, 5),
        "bank_account_count": (2, 1), "ifsc_count": (2, 1),
        "credit_card_count": (1, 0.5), "upi_count": (1, 0.5),
        "money_count": (20, 10), "pan_count": (1, 0.5),
        "phone_count": (1, 0.5), "address_count": (1, 0.5),
        "table_count": (3, 1), "header_count": (2, 1), "footer_count": (2, 1),
    },
    "Insurance Document": {
        "num_pages": (8, 4), "total_words": (3500, 1500),
        "person_count": (3, 1), "org_count": (3, 1), "date_count": (6, 3),
        "aadhaar_count": (1, 0.5), "pan_count": (1, 0.5),
        "bank_account_count": (1, 0.5), "phone_count": (2, 1),
        "email_count": (1, 0.5), "address_count": (2, 1),
        "money_count": (5, 3), "signature_count": (2, 1), "stamp_count": (1, 0.5),
        "table_count": (2, 1), "header_count": (3, 1), "footer_count": (2, 1),
    },
    "Property Agreement": {
        "num_pages": (12, 5), "total_words": (6000, 2500),
        "person_count": (4, 2), "org_count": (2, 1), "date_count": (8, 3),
        "aadhaar_count": (2, 1), "pan_count": (2, 1),
        "address_count": (4, 2), "money_count": (4, 2),
        "stamp_count": (3, 1), "signature_count": (3, 1),
        "law_count": (3, 2), "location_count": (3, 2),
        "table_count": (1, 0.5), "header_count": (4, 2), "footer_count": (3, 1),
    },
}

HYPERPARAMETER_GRIDS: Dict[str, Dict[str, List]] = {
    "LogisticRegression": {
        "C": [1.0],
        "solver": ["lbfgs"],
        "max_iter": [500],
    },
    "RandomForest": {
        "n_estimators": [100],
        "max_depth": [10, None],
        "min_samples_split": [2],
        "min_samples_leaf": [1],
    },
    "GradientBoosting": {
        "n_estimators": [100],
        "learning_rate": [0.1],
        "max_depth": [3],
        "min_samples_split": [2],
    },
    "XGBoost": {
        "n_estimators": [100],
        "learning_rate": [0.1],
        "max_depth": [3],
        "subsample": [1.0],
        "colsample_bytree": [1.0],
    },
}
