"""
Hybrid Dataset Generator — Level 1 Machine Learning Baseline
Generates training data from real processed documents + synthetic legal document profiles.
Configurable size: 500 / 5,000 / 10,000 / 50,000 samples.
"""
import logging
import os
import uuid
import json
from datetime import datetime
from typing import Dict, Any, List, Optional

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from models.document import Document
from models.ml_models import TrainingDataset
from services.ml.config import (
    ALL_FEATURE_NAMES, DOCUMENT_TYPE_PROFILES, SENSITIVITY_CLASSES,
    DEFAULT_RANDOM_SEED, DEFAULT_DATASET_SIZE, GENERATOR_VERSION,
    PREPROCESSING_VERSION, FEATURE_SET_VERSION, LABELING_RULE_VERSION,
    apply_sensitivity_label,
)
from services.ml.feature_extractor import FeatureExtractor

logger = logging.getLogger("redactai.ml.dataset_generator")

# Directory for persisted ML artifacts
ML_MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "ml_models")


class DatasetGenerator:
    """Hybrid dataset generator combining real + synthetic document features."""

    def __init__(self, db: Session):
        self.db = db
        self.feature_extractor = FeatureExtractor(db)
        os.makedirs(ML_MODELS_DIR, exist_ok=True)

    def generate(
        self,
        total_size: int = DEFAULT_DATASET_SIZE,
        random_seed: int = DEFAULT_RANDOM_SEED,
    ) -> Dict[str, Any]:
        """
        Generate a hybrid training dataset.

        1. Extract features from real processed documents.
        2. Fill remaining volume with synthetic samples.
        3. Apply deterministic labeling rules.
        4. Save CSV and register in DB.

        Returns:
            Dict with dataset metadata and file path.
        """
        rng = np.random.RandomState(random_seed)
        logger.info(f"Generating hybrid dataset: target_size={total_size}, seed={random_seed}")

        # ─── Phase 1: Real Documents ───────────────────────────────
        real_features = self._extract_real_documents()
        real_count = len(real_features)
        logger.info(f"Extracted {real_count} real document feature vectors.")

        # ─── Phase 2: Synthetic Documents ──────────────────────────
        synthetic_count = max(total_size - real_count, 0)
        synthetic_features = self._generate_synthetic(synthetic_count, rng)
        logger.info(f"Generated {len(synthetic_features)} synthetic feature vectors.")

        # ─── Phase 3: Combine & Label ──────────────────────────────
        all_features = real_features + synthetic_features

        # Apply deterministic sensitivity labels
        for row in all_features:
            row["sensitivity_label"] = apply_sensitivity_label(row)

        # Convert to DataFrame
        columns = ALL_FEATURE_NAMES + ["document_type", "sensitivity_label"]
        df = pd.DataFrame(all_features, columns=columns)

        # Ensure correct types
        for col in ALL_FEATURE_NAMES:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

        # ─── Phase 4: Save Artifacts ───────────────────────────────
        dataset_version = f"v1.{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        csv_path = os.path.join(ML_MODELS_DIR, "training_dataset.csv")
        df.to_csv(csv_path, index=False)
        logger.info(f"Dataset saved to {csv_path}")

        # Class distribution
        class_dist = df["sensitivity_label"].value_counts().to_dict()
        doc_type_dist = df["document_type"].value_counts().to_dict()

        # Determine source type
        if real_count == 0:
            source = "synthetic"
        elif synthetic_count == 0:
            source = "real"
        else:
            source = "hybrid"

        # Register dataset in DB
        dataset_record = TrainingDataset(
            id=uuid.uuid4(),
            dataset_version=dataset_version,
            dataset_source=source,
            generator_version=GENERATOR_VERSION,
            preprocessing_version=PREPROCESSING_VERSION,
            feature_set_version=FEATURE_SET_VERSION,
            labeling_rule_version=LABELING_RULE_VERSION,
            random_seed=random_seed,
            total_samples=len(df),
            real_samples=real_count,
            synthetic_samples=len(synthetic_features),
            feature_count=len(ALL_FEATURE_NAMES),
            class_distribution=class_dist,
            document_type_distribution=doc_type_dist,
            file_path=csv_path,
        )
        self.db.add(dataset_record)
        self.db.commit()

        logger.info(f"Dataset registered: version={dataset_version}, samples={len(df)}, source={source}")

        return {
            "dataset_id": str(dataset_record.id),
            "dataset_version": dataset_version,
            "total_samples": len(df),
            "real_samples": real_count,
            "synthetic_samples": len(synthetic_features),
            "feature_count": len(ALL_FEATURE_NAMES),
            "class_distribution": class_dist,
            "document_type_distribution": doc_type_dist,
            "source": source,
            "file_path": csv_path,
        }

    def _extract_real_documents(self) -> List[Dict[str, Any]]:
        """Extract feature vectors from all processed documents in the database."""
        docs = self.db.query(Document).filter(Document.status == "Processed").all()
        real_features = []

        for doc in docs:
            try:
                features = self.feature_extractor.extract(doc.id)
                if features:
                    features["document_type"] = "Real"
                    real_features.append(features)
            except Exception as e:
                logger.warning(f"Failed to extract features for document {doc.id}: {e}")

        return real_features

    def _generate_synthetic(self, count: int, rng: np.random.RandomState) -> List[Dict[str, Any]]:
        """Generate synthetic feature vectors based on document type profiles."""
        if count <= 0:
            return []

        doc_types = list(DOCUMENT_TYPE_PROFILES.keys())
        samples_per_type = count // len(doc_types)
        remainder = count % len(doc_types)

        synthetic = []

        for i, doc_type in enumerate(doc_types):
            n = samples_per_type + (1 if i < remainder else 0)
            profile = DOCUMENT_TYPE_PROFILES[doc_type]

            for _ in range(n):
                features = self._generate_single_sample(profile, doc_type, rng)
                synthetic.append(features)

        return synthetic

    def _generate_single_sample(
        self,
        profile: Dict[str, Any],
        doc_type: str,
        rng: np.random.RandomState,
    ) -> Dict[str, Any]:
        """Generate a single synthetic feature vector from a document type profile."""
        features: Dict[str, Any] = {name: 0 for name in ALL_FEATURE_NAMES}

        # Fill raw features from profile (mean, std) using normal distribution, floor to 0
        for feature_name, (mean, std) in profile.items():
            if feature_name in features:
                val = rng.normal(mean, std)
                # Integer features get rounded; floats stay as-is
                if feature_name in ("avg_confidence", "max_confidence", "pii_density", "entity_density"):
                    features[feature_name] = round(max(val, 0), 4)
                else:
                    features[feature_name] = max(int(round(val)), 0)

        # Derive remaining basic features
        if features["total_words"] == 0:
            features["total_words"] = max(int(rng.normal(2000, 800)), 100)
        features["total_characters"] = features["total_words"] * int(rng.normal(5, 1))
        features["avg_sentence_length"] = round(rng.normal(18, 5), 2)
        features["avg_sentence_length"] = max(features["avg_sentence_length"], 5)
        if features["num_pages"] == 0:
            features["num_pages"] = 1

        # Metadata features
        features["language_encoded"] = rng.choice([1, 1, 1, 1, 2, 3, 0], p=[0.55, 0.15, 0.1, 0.05, 0.05, 0.05, 0.05])
        features["is_encrypted"] = int(rng.random() < 0.05)
        features["has_digital_signature"] = 1 if features.get("signature_count", 0) > 0 else int(rng.random() < 0.3)
        features["has_producer"] = int(rng.random() < 0.7)
        features["has_author"] = int(rng.random() < 0.4)

        # Compute risk counts from entity presence
        # Assign risk based on entity types using the same mapping as the orchestrator
        critical_entities = features["aadhaar_count"] + features.get("passport_count", 0) + features.get("bank_account_count", 0)
        high_entities = features["pan_count"] + features.get("driving_license_count", 0) + features.get("voter_id_count", 0) + features.get("ifsc_count", 0) + features.get("credit_card_count", 0) + features.get("upi_count", 0)
        medium_entities = features["phone_count"] + features["email_count"] + features["address_count"] + features.get("money_count", 0) + features.get("law_count", 0) + features.get("court_count", 0) + features.get("judge_count", 0) + features.get("case_number_count", 0)
        low_entities = features["person_count"] + features["org_count"] + features.get("location_count", 0) + features.get("date_count", 0)

        features["critical_count"] = critical_entities
        features["high_count"] = high_entities
        features["medium_count"] = medium_entities
        features["low_count"] = low_entities

        # Confidence
        if (critical_entities + high_entities + medium_entities + low_entities) > 0:
            features["avg_confidence"] = round(rng.uniform(0.65, 0.98), 4)
            features["max_confidence"] = round(min(features["avg_confidence"] + rng.uniform(0, 0.15), 1.0), 4)
        else:
            features["avg_confidence"] = 0
            features["max_confidence"] = 0

        # Compute engineered features
        features = self._compute_engineered(features)

        # Tag document type
        from services.ml.config import DOCUMENT_TYPE_ENCODING
        features["document_type"] = doc_type
        features["document_type_encoded"] = DOCUMENT_TYPE_ENCODING.get(doc_type, 0)

        return features

    def _compute_engineered(self, f: Dict[str, Any]) -> Dict[str, Any]:
        """Compute engineered features from raw values (mirrors FeatureExtractor logic)."""
        total_words = max(f["total_words"], 1)
        num_pages = max(f["num_pages"], 1)

        pii_keys = [
            "aadhaar_count", "pan_count", "passport_count", "driving_license_count",
            "voter_id_count", "email_count", "phone_count", "address_count",
            "bank_account_count", "credit_card_count", "ifsc_count", "upi_count",
        ]
        entity_keys = [
            "person_count", "org_count", "location_count", "date_count",
            "money_count", "court_count", "judge_count", "law_count",
            "case_number_count",
        ]
        total_pii = sum(f.get(k, 0) for k in pii_keys)
        total_entities = sum(f.get(k, 0) for k in entity_keys) + total_pii
        total_risk = f["critical_count"] + f["high_count"] + f["medium_count"] + f["low_count"]

        f["pii_density"] = round(total_pii / total_words * 1000, 4)
        f["entity_density"] = round(total_entities / total_words * 1000, 4)
        f["risk_density"] = round(total_risk / total_words * 1000, 4)
        f["critical_ratio"] = round(f["critical_count"] / max(total_risk, 1), 4)
        f["avg_entities_per_page"] = round(total_entities / num_pages, 4)
        f["avg_pii_per_page"] = round(total_pii / num_pages, 4)

        if total_words < 500:
            f["doc_length_category"] = 1
        elif total_words < 2000:
            f["doc_length_category"] = 2
        elif total_words < 5000:
            f["doc_length_category"] = 3
        else:
            f["doc_length_category"] = 4

        f["contains_gov_id"] = 1 if (f["aadhaar_count"] + f.get("passport_count", 0) + f.get("voter_id_count", 0) + f.get("driving_license_count", 0)) > 0 else 0
        f["contains_financial_data"] = 1 if (f.get("bank_account_count", 0) + f.get("credit_card_count", 0) + f.get("ifsc_count", 0) + f.get("upi_count", 0) + f.get("money_count", 0)) > 0 else 0
        f["contains_legal_terms"] = 1 if (f.get("law_count", 0) + f.get("court_count", 0) + f.get("judge_count", 0) + f.get("case_number_count", 0)) > 0 else 0
        f["contains_personal_data"] = 1 if (f["person_count"] + f["phone_count"] + f["email_count"] + f["address_count"]) > 0 else 0

        return f
