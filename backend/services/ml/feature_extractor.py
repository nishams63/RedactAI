"""
Feature Extractor — Level 1 Machine Learning Baseline
Extracts ~50 structured features from a processed document by querying
the Document Intelligence Layer tables.
"""
import logging
import uuid
from typing import Dict, Any, Optional, List

from sqlalchemy.orm import Session

from models.document import Document
from models.document_intelligence import (
    DocumentMetadata, DocumentPage, DocumentBlock, DocumentEntity,
)
from services.ml.config import (
    ALL_FEATURE_NAMES, ENTITY_TYPE_TO_FEATURE, BLOCK_TYPE_TO_FEATURE,
    RISK_LEVEL_TO_FEATURE, LANGUAGE_ENCODING, DOCUMENT_TYPE_ENCODING,
)

logger = logging.getLogger("redactai.ml.feature_extractor")


class FeatureExtractor:
    """Extracts a single feature vector from a processed document."""

    def __init__(self, db: Session):
        self.db = db

    def extract(self, document_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        """
        Extract all features for one document.

        Returns:
            Dict of feature_name -> value, or None if document not found.
        """
        doc = self.db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            logger.warning(f"Document {document_id} not found for feature extraction.")
            return None

        # Initialize all features to 0
        features: Dict[str, Any] = {name: 0 for name in ALL_FEATURE_NAMES}

        # ─── Query related intelligence data ───────────────────────
        metadata = self.db.query(DocumentMetadata).filter(
            DocumentMetadata.document_id == document_id
        ).first()

        pages = self.db.query(DocumentPage).filter(
            DocumentPage.document_id == document_id
        ).order_by(DocumentPage.page_number.asc()).all()

        blocks = self.db.query(DocumentBlock).filter(
            DocumentBlock.document_id == document_id
        ).all()

        entities = self.db.query(DocumentEntity).filter(
            DocumentEntity.document_id == document_id
        ).all()

        # ─── Basic Features ────────────────────────────────────────
        features["num_pages"] = len(pages) if pages else (metadata.page_count if metadata else 1)

        full_text = " ".join(p.text for p in pages) if pages else ""
        words = full_text.split()
        features["total_words"] = len(words)
        features["total_characters"] = len(full_text)

        sentences = [s.strip() for s in full_text.replace("!", ".").replace("?", ".").split(".") if s.strip()]
        features["avg_sentence_length"] = (
            round(len(words) / max(len(sentences), 1), 2)
        )

        # ─── Document Structure ────────────────────────────────────
        for block in blocks:
            feature_key = BLOCK_TYPE_TO_FEATURE.get(block.block_type)
            if feature_key and feature_key in features:
                features[feature_key] += 1

        # ─── Entity Counts & Risk Metrics ──────────────────────────
        confidences: List[float] = []
        for entity in entities:
            # Entity type count
            feature_key = ENTITY_TYPE_TO_FEATURE.get(entity.entity_type)
            if feature_key and feature_key in features:
                features[feature_key] += 1

            # Risk level count
            risk_key = RISK_LEVEL_TO_FEATURE.get(entity.risk_level)
            if risk_key and risk_key in features:
                features[risk_key] += 1

            # Confidence tracking
            if entity.confidence is not None:
                confidences.append(entity.confidence)

        # ─── Confidence Metrics ────────────────────────────────────
        if confidences:
            features["avg_confidence"] = round(sum(confidences) / len(confidences), 4)
            features["max_confidence"] = round(max(confidences), 4)

        # ─── Document Metadata ─────────────────────────────────────
        if metadata:
            lang_name = metadata.language or "Unknown"
            features["language_encoded"] = LANGUAGE_ENCODING.get(lang_name, 0)
            features["is_encrypted"] = 1 if metadata.encryption_status == "ENCRYPTED" else 0
            features["has_digital_signature"] = 1 if metadata.signature_status == "SIGNED" else 0
            features["has_producer"] = 1 if metadata.producer else 0
            features["has_author"] = 1 if metadata.author else 0

        # ─── Engineered Features ───────────────────────────────────
        features = self._compute_engineered_features(features)

        # Determine document type from title
        doc_type = "NDA"
        title_lower = doc.title.lower() if doc.title else ""
        if "nda" in title_lower:
            doc_type = "NDA"
        elif "employment" in title_lower or "emp_" in title_lower:
            doc_type = "Employment Contract"
        elif "service" in title_lower:
            doc_type = "Service Agreement"
        elif "invoice" in title_lower:
            doc_type = "Invoice"
        elif "gov" in title_lower:
            doc_type = "Government Form"
        elif "med" in title_lower:
            doc_type = "Medical Record"
        elif "court" in title_lower:
            doc_type = "Court Order"
        elif "notice" in title_lower:
            doc_type = "Legal Notice"

        features["document_type"] = doc_type
        features["document_type_encoded"] = DOCUMENT_TYPE_ENCODING.get(doc_type, 0)

        logger.info(f"Extracted {len(features)} features for document {document_id} (type: {doc_type}).")
        return features

    def _compute_engineered_features(self, f: Dict[str, Any]) -> Dict[str, Any]:
        """Compute derived/engineered features from raw feature values."""
        total_words = max(f["total_words"], 1)
        num_pages = max(f["num_pages"], 1)

        # PII total
        pii_features = [
            "aadhaar_count", "pan_count", "passport_count", "driving_license_count",
            "voter_id_count", "email_count", "phone_count", "address_count",
            "bank_account_count", "credit_card_count", "ifsc_count", "upi_count",
        ]
        total_pii = sum(f.get(k, 0) for k in pii_features)

        entity_features = [
            "person_count", "org_count", "location_count", "date_count",
            "money_count", "court_count", "judge_count", "law_count",
            "case_number_count",
        ]
        total_entities = sum(f.get(k, 0) for k in entity_features) + total_pii

        total_risk = f["critical_count"] + f["high_count"] + f["medium_count"] + f["low_count"]

        # Density features
        f["pii_density"] = round(total_pii / total_words * 1000, 4)
        f["entity_density"] = round(total_entities / total_words * 1000, 4)
        f["risk_density"] = round(total_risk / total_words * 1000, 4)
        f["critical_ratio"] = round(f["critical_count"] / max(total_risk, 1), 4)

        # Per-page features
        f["avg_entities_per_page"] = round(total_entities / num_pages, 4)
        f["avg_pii_per_page"] = round(total_pii / num_pages, 4)

        # Document length category (ordinal: 1=short, 2=medium, 3=long, 4=very_long)
        if total_words < 500:
            f["doc_length_category"] = 1
        elif total_words < 2000:
            f["doc_length_category"] = 2
        elif total_words < 5000:
            f["doc_length_category"] = 3
        else:
            f["doc_length_category"] = 4

        # Boolean aggregates
        f["contains_gov_id"] = 1 if (f["aadhaar_count"] + f["passport_count"] + f["voter_id_count"] + f["driving_license_count"]) > 0 else 0
        f["contains_financial_data"] = 1 if (f["bank_account_count"] + f["credit_card_count"] + f["ifsc_count"] + f["upi_count"] + f["money_count"]) > 0 else 0
        f["contains_legal_terms"] = 1 if (f["law_count"] + f["court_count"] + f["judge_count"] + f["case_number_count"]) > 0 else 0
        f["contains_personal_data"] = 1 if (f["person_count"] + f["phone_count"] + f["email_count"] + f["address_count"]) > 0 else 0

        return f
