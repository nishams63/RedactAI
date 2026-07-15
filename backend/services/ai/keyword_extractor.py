"""Module 8 - Keyword Extractor.

Automatically extracts legal terms, risk/compliance keywords, priority terms,
and generates keyword summaries of documents.
"""
import re
import logging
from collections import Counter
from typing import Dict, Any, List, Set

logger = logging.getLogger("redactai.ai.keyword_extractor")

# Basic local stopwords list to avoid external dependency issues
STOPWORDS = {
    'i', 'me', 'my', 'myself', 'we', 'our', 'ours', 'ourselves', 'you', "you're", "you've", "you'll", "you'd",
    'your', 'yours', 'yourself', 'yourselves', 'he', 'him', 'his', 'himself', 'she', "she's", 'her', 'hers',
    'herself', 'it', "it's", 'its', 'itself', 'they', 'them', 'their', 'theirs', 'themselves', 'what', 'which',
    'who', 'whom', 'this', 'that', "that'll", 'these', 'those', 'am', 'is', 'are', 'was', 'were', 'be', 'been',
    'being', 'have', 'has', 'had', 'having', 'do', 'does', 'did', 'doing', 'a', 'an', 'the', 'and', 'but', 'if',
    'or', 'because', 'as', 'until', 'while', 'of', 'at', 'by', 'for', 'with', 'about', 'against', 'between',
    'into', 'through', 'during', 'before', 'after', 'above', 'below', 'to', 'from', 'up', 'down', 'in', 'out',
    'on', 'off', 'over', 'under', 'again', 'further', 'then', 'once', 'here', 'there', 'when', 'where', 'why',
    'how', 'all', 'any', 'both', 'each', 'few', 'more', 'most', 'other', 'some', 'such', 'no', 'nor', 'not',
    'only', 'own', 'same', 'so', 'than', 'too', 'very', 's', 't', 'can', 'will', 'just', 'don', "don't", 'should',
    "should've", 'now', 'd', 'll', 'm', 'o', 're', 've', 'y', 'ain', 'aren', "aren't", 'couldn', "couldn't",
    'didn', "didn't", 'doesn', "doesn't", 'hadn', "hadn't", 'hasn', "hasn't", 'haven', "haven't", 'isn', "isn't",
    'ma', 'mightn', "mightn't", 'mustn', "mustn't", 'needn', "needn't", 'shan', "shan't", 'shouldn', "shouldn't",
    'wasn', "wasn't", 'weren', "weren't", 'won', "won't", 'wouldn', "wouldn't", "shall", "may", "hereby", "thereof",
    "hereto", "therein", "agreement", "party", "parties", "contract", "under", "said", "agreement", "document"
}

LEGAL_LEXICON = {
    "indemnity", "liability", "termination", "confidentiality", "severability", "arbitration",
    "force majeure", "intellectual property", "warranty", "covenant", "jurisdiction", "solicitor",
    "preamble", "remedy", "notary", "infringement", "witnesseth", "injunction", "damages", "liquidated",
    "non-disclosure", "dissemination", "proprietary", "trade secret", "exclusivity", "recitals"
}

RISK_LEXICON = {
    "breach", "penalty", "damage", "infringement", "negligence", "fine", "forfeit", "default",
    "indemnify", "liability", "termination", "unauthorized", "leak", "compromise", "violation",
    "dispute", "litigation", "lawsuit", "court", "claims"
}

COMPLIANCE_LEXICON = {
    "gdpr", "privacy", "consent", "data fiduciary", "compliance", "regulation", "governance",
    "audit", "dpdp", "personal data", "masking", "redact", "retention", "security measures",
    "disclosure", "notice", "legislative", "policy", "standards", "compliance officer"
}

class LegalKeywordExtractor:
    def clean_and_tokenize(self, text: str) -> List[str]:
        """Cleans, lowercases, and splits text into single words, removing punctuation and stopwords."""
        if not text:
            return []
        
        words = re.findall(r'\b[a-zA-Z]{3,20}\b', text.lower())
        return [w for w in words if w not in STOPWORDS]

    def extract_keywords(self, text: str, top_n: int = 15) -> Dict[str, Any]:
        """Extracts legal terms, risk/compliance keywords, and builds top keywords summary."""
        cleaned_words = self.clean_and_tokenize(text)
        word_counts = Counter(cleaned_words)
        
        # 1. Top general keywords
        top_keywords = [{"word": word, "frequency": count} for word, count in word_counts.most_common(top_n)]
        
        # 2. Extract legal terms
        detected_legal = []
        for term in LEGAL_LEXICON:
            # Handle multi-word lexicon items (e.g. force majeure)
            if term in text.lower():
                count = text.lower().count(term)
                if count > 0:
                    detected_legal.append({"word": term, "frequency": count})
        detected_legal.sort(key=lambda x: x["frequency"], reverse=True)
        
        # 3. Extract risk terms
        detected_risk = []
        for term in RISK_LEXICON:
            count = text.lower().count(term)
            if count > 0:
                detected_risk.append({"word": term, "frequency": count})
        detected_risk.sort(key=lambda x: x["frequency"], reverse=True)
        
        # 4. Extract compliance terms
        detected_compliance = []
        for term in COMPLIANCE_LEXICON:
            count = text.lower().count(term)
            if count > 0:
                detected_compliance.append({"word": term, "frequency": count})
        detected_compliance.sort(key=lambda x: x["frequency"], reverse=True)

        # 5. Generate summary snippet using high-score sentences containing top keywords
        summary_sentences = []
        sentences = [s.strip() for s in re.split(r'\. |\n', text) if s.strip()]
        
        # Score sentences based on keyword matches
        top_words_set = {item["word"] for item in top_keywords[:5]}
        scored_sentences = []
        for s in sentences:
            score = sum(1 for w in s.lower().split() if w in top_words_set)
            # Penalize super long or super short sentences
            if 15 < len(s.split()) < 40:
                scored_sentences.append((s, score))
                
        scored_sentences.sort(key=lambda x: x[1], reverse=True)
        # Take top 3 sentences to form a keyword-based summary
        summary = " ".join(item[0] for item in scored_sentences[:3])
        if not summary:
            summary = text[:300] + "..."

        return {
            "top_keywords": top_keywords,
            "legal_terms": detected_legal[:10],
            "risk_keywords": detected_risk[:10],
            "compliance_keywords": detected_compliance[:10],
            "summary": summary
        }

keyword_extractor = LegalKeywordExtractor()
