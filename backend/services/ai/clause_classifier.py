"""Module 3 - Legal Clause Classifier.

Uses a hybrid TF-IDF keyword match and Local Sentence Embedding similarity to classify clauses.
Categories: Confidentiality, Termination, Liability, Payment, Governing Law, Arbitration, Non-Disclosure, Employment, Privacy, Intellectual Property.
"""
import re
import numpy as np
import logging
from typing import Dict, Any, List, Tuple
from services.legal_ai.embedder import LocalSentenceEmbedder

logger = logging.getLogger("redactai.ai.clause_classifier")

# 10 categories of target clauses
CATEGORIES = [
    "Confidentiality",
    "Termination",
    "Liability",
    "Payment",
    "Governing Law",
    "Arbitration",
    "Non-Disclosure",
    "Employment",
    "Privacy",
    "Intellectual Property"
]

# Keywords characterizing each category (acts as a light TF-IDF matching system)
CATEGORY_KEYWORDS = {
    "Confidentiality": ["confidential", "proprietary", "disclosure", "secret", "nondisclosure", "information", "restrict"],
    "Termination": ["terminate", "termination", "expiration", "expiry", "breach", "notice period", "cancel", "rescind"],
    "Liability": ["liability", "indemnify", "indemnity", "hold harmless", "damage", "negligence", "liability cap"],
    "Payment": ["payment", "fee", "invoice", "price", "billing", "amount", "salary", "reimburse", "compensation"],
    "Governing Law": ["governing law", "jurisdiction", "construed in accordance", "laws of", "state of", "courts of"],
    "Arbitration": ["arbitration", "arbitrate", "dispute resolution", "arbitrator", "tribunal", "mediate", "mediation"],
    "Non-Disclosure": ["non-disclosure", "nda", "disclosure of information", "secret information", "receiving party", "disclosing party"],
    "Employment": ["employment", "employee", "employer", "job title", "salary", "bonus", "benefits", "probation"],
    "Privacy": ["privacy", "personal data", "gdpr", "dpdp", "data fiduciary", "data protection", "processing", "consent"],
    "Intellectual Property": ["intellectual property", "patent", "copyright", "trademark", "invention", "ownership", "licensor", "proprietary right"]
}

# Anchor sentences representing the semantic concepts of the categories
CATEGORY_ANCHORS = {
    "Confidentiality": [
        "Each party agrees to maintain all confidential information in strict confidence.",
        "The receiving party shall not disclose or use the proprietary information of the disclosing party.",
        "Confidential information includes all trade secrets and proprietary data."
    ],
    "Termination": [
        "Either party may terminate this agreement upon thirty days written notice.",
        "This contract shall terminate immediately upon material breach of its provisions.",
        "Upon termination of the agreement, all obligations and licenses shall cease."
    ],
    "Liability": [
        "In no event shall either party be liable for any consequential or indirect damages.",
        "The total liability of the service provider under this agreement is capped at the total fees paid.",
        "The client agrees to indemnify and hold harmless the vendor from any third-party claims."
    ],
    "Payment": [
        "Payments shall be made within thirty days of invoice receipt.",
        "The customer shall pay the fees described in the fee schedule.",
        "Late payments shall accrue interest at the rate of one percent per month."
    ],
    "Governing Law": [
        "This agreement is governed by and construed in accordance with the laws of India.",
        "The courts of Mumbai shall have exclusive jurisdiction over any disputes.",
        "This contract shall be interpreted under the governing law of Delhi."
    ],
    "Arbitration": [
        "Any dispute arising out of this contract shall be referred to arbitration.",
        "The arbitration shall be conducted by a sole arbitrator in accordance with the Arbitration Act.",
        "Disputes shall be settled under the rules of the International Chamber of Commerce."
    ],
    "Non-Disclosure": [
        "This non-disclosure section governs the exchange of sensitive information.",
        "The parties entering this NDA agree to protect shared secrets.",
        "Information shared under this non-disclosure clause will remain confidential."
    ],
    "Employment": [
        "The employee is hired as a software engineer reporting to the director.",
        "The employer agrees to pay the employee a monthly base salary.",
        "This employment relationship is subject to a three month probation period."
    ],
    "Privacy": [
        "We protect personal data in compliance with the Data Protection Act.",
        "The processing of personal data requires explicit and informed consent.",
        "The data fiduciary shall take appropriate measures to secure personal information."
    ],
    "Intellectual Property": [
        "All intellectual property rights developed under this agreement belong to the client.",
        "The vendor retains all patents, copyrights, and trademarks pre-dating this contract.",
        "This license grants no ownership rights over the proprietary software."
    ]
}

class LegalClauseClassifier:
    def __init__(self):
        self.embedder = LocalSentenceEmbedder()
        self.anchor_embeddings = {}
        self._precompute_anchors()

    def _precompute_anchors(self):
        """Precomputes vector embeddings for the category anchor sentences."""
        logger.info("Precomputing anchor embeddings for clause classification...")
        try:
            for cat, sentences in CATEGORY_ANCHORS.items():
                embeddings = self.embedder.get_embeddings(sentences)
                self.anchor_embeddings[cat] = np.mean(embeddings, axis=0)
            logger.info("Successfully precomputed clause classifier anchors.")
        except Exception as e:
            logger.error(f"Failed to precompute anchors: {e}")
            # Mock vectors if loading fails
            for cat in CATEGORIES:
                self.anchor_embeddings[cat] = np.random.normal(0, 1, 384)

    def _compute_keyword_score(self, text: str, category: str) -> float:
        """Computes TF-IDF styled keyword overlap score."""
        lower_text = text.lower()
        score = 0.0
        keywords = CATEGORY_KEYWORDS[category]
        for kw in keywords:
            if kw in lower_text:
                score += 1.0
        return score / len(keywords)

    def classify_clause(self, text: str) -> Dict[str, Any]:
        """Classifies a clause text into one of the 10 categories, returning confidence scores."""
        if not text or len(text.strip()) < 10:
            return {
                "clause_type": "General / Miscellaneous",
                "confidence": 1.0,
                "scores": {cat: 0.0 for cat in CATEGORIES}
            }

        try:
            # Get sentence embedding of the clause
            clause_vector = np.array(self.embedder.get_embedding(text))
            
            raw_scores = {}
            for cat in CATEGORIES:
                # 1. Semantic Cosine Similarity
                anchor_vector = self.anchor_embeddings[cat]
                sim = np.dot(clause_vector, anchor_vector) / (np.linalg.norm(clause_vector) * np.linalg.norm(anchor_vector) + 1e-9)
                # Map to [0, 1] range
                semantic_score = max(0.0, float(sim))
                
                # 2. Keyword score
                kw_score = self._compute_keyword_score(text, cat)
                
                # Combined score (70% Semantic, 30% Keyword overlap)
                raw_scores[cat] = (0.7 * semantic_score) + (0.3 * kw_score)
            
            # Apply softmax or normalize to get probability distribution
            exp_scores = {cat: np.exp(val * 8) for cat, val in raw_scores.items()} # Amplifying differences
            sum_exp = sum(exp_scores.values())
            normalized_scores = {cat: float(exp_scores[cat] / sum_exp) for cat in CATEGORIES}
            
            # Find best match
            best_cat = max(normalized_scores, key=normalized_scores.get)
            best_score = normalized_scores[best_cat]
            
            # If the best score is very low, mark as General/Miscellaneous
            if best_score < 0.20:
                best_cat = "General / Miscellaneous"

            return {
                "clause_type": best_cat,
                "confidence": round(best_score, 4),
                "scores": {cat: round(val, 4) for cat, val in normalized_scores.items()}
            }
        except Exception as e:
            logger.error(f"Error during clause classification: {e}")
            return {
                "clause_type": "General / Miscellaneous",
                "confidence": 1.0,
                "scores": {cat: 0.1 for cat in CATEGORIES}
            }

clause_classifier = LegalClauseClassifier()
