"""Module 1 - Advanced Legal NLP Preprocessor.

Performs unicode/text normalization, OCR noise correction, legal abbreviation expansion,
tokenization benchmarking, POS tagging, lemmatization, dependency parsing, and language detection.
"""
import re
import time
import logging
import unicodedata
from typing import Dict, Any, List

logger = logging.getLogger("redactai.ai.preprocessor")

LEGAL_ABBREVIATIONS = {
    r"\bu/s\b": "under section",
    r"\bv\.": "versus",
    r"\bvs\.": "versus",
    r"\bCo\.": "Company",
    r"\bLtd\.": "Limited",
    r"\bIPC\b": "Indian Penal Code",
    r"\bCrPC\b": "Code of Criminal Procedure",
    r"\bSec\.": "Section",
    r"\bSect\.": "Section",
    r"\bCl\.": "Clause",
    r"\bArt\.": "Article",
    r"\bGovt\.": "Government",
    r"\bw\.e\.f\.": "with effect from",
    r"\bNDA\b": "Non-Disclosure Agreement",
    r"\bIP\b": "Intellectual Property",
    r"\bPII\b": "Personally Identifiable Information",
}

class LegalTextPreprocessor:
    def __init__(self):
        self.nlp = None
        try:
            import spacy
            self.nlp = spacy.load("en_core_web_sm")
            logger.info("spaCy en_core_web_sm loaded for preprocessor.")
        except Exception as e:
            logger.error(f"Failed to load spaCy model for preprocessor: {e}")

    def normalize_unicode(self, text: str) -> str:
        """Applies NFKC Unicode normalization."""
        if not text:
            return ""
        return unicodedata.normalize("NFKC", text)

    def normalize_text(self, text: str) -> str:
        """Standardizes quotation marks, hyphens, and collapses whitespaces."""
        if not text:
            return ""
        # Standardize quotes
        text = re.sub(r'[\u201c\u201d\u201e\u201f\u0022\u2033\u2036]', '"', text)
        text = re.sub(r'[\u2018\u2019\u201a\u201b\u0027\u2032\u2035]', "'", text)
        # Standardize hyphens/dashes
        text = re.sub(r'[\u2010\u2011\u2012\u2013\u2014\u2015\u2212]', '-', text)
        # Collapse multiple spaces and newlines
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r'\r\n|\r|\n', '\n', text)
        return text.strip()

    def correct_ocr_noise(self, text: str) -> str:
        """Cleans common OCR artifact patterns and stray characters."""
        if not text:
            return ""
        # Replace stray '|' or 'l' in numerical lists or contexts
        text = re.sub(r'\|\s*', ' ', text)
        # Fix common OCR word breaks at lines
        text = re.sub(r'(\w+)-\n(\w+)', r'\1\2', text)
        # Clean non-printable character artifacts
        text = "".join(ch for ch in text if unicodedata.category(ch)[0] != "C" or ch in ("\n", "\t"))
        return text

    def expand_abbreviations(self, text: str) -> str:
        """Expands legal abbreviations into their full terms."""
        if not text:
            return ""
        expanded = text
        for abbr, full in LEGAL_ABBREVIATIONS.items():
            # Match case-insensitively but preserve context
            expanded = re.sub(abbr, full, expanded, flags=re.IGNORECASE)
        return expanded

    def detect_language(self, text: str) -> str:
        """Detects primary language using langdetect."""
        if not text or not text.strip():
            return "English"
        try:
            from langdetect import detect
            # Use top 1000 characters for speed and robustness
            lang_code = detect(text[:1000])
            lang_map = {
                "en": "English",
                "hi": "Hindi",
                "ta": "Tamil",
                "ml": "Malayalam",
                "te": "Telugu",
                "kn": "Kannada"
            }
            return lang_map.get(lang_code, "English")
        except Exception as e:
            logger.warning(f"Language detection failed, fallback to English: {e}")
            return "English"

    def benchmark_tokenizers(self, text: str) -> Dict[str, Any]:
        """Benchmarks speed of character, word, and subword tokenization."""
        metrics = {}
        if not text:
            return metrics

        # 1. Character Tokenizer
        start = time.perf_counter()
        char_tokens = list(text)
        char_time = (time.perf_counter() - start) * 1000  # ms
        metrics["character"] = {
            "token_count": len(char_tokens),
            "latency_ms": round(char_time, 4),
            "speed_tokens_per_ms": round(len(char_tokens) / (char_time + 1e-9), 2)
        }

        # 2. Word Tokenizer
        start = time.perf_counter()
        word_tokens = re.findall(r'\w+|[^\w\s]', text)
        word_time = (time.perf_counter() - start) * 1000  # ms
        metrics["word"] = {
            "token_count": len(word_tokens),
            "latency_ms": round(word_time, 4),
            "speed_tokens_per_ms": round(len(word_tokens) / (word_time + 1e-9), 2)
        }

        # 3. Subword Tokenizer
        subword_count = 0
        subword_time = 0.0
        try:
            from transformers import AutoTokenizer
            start = time.perf_counter()
            tokenizer = AutoTokenizer.from_pretrained("sentence-transformers/all-MiniLM-L6-v2")
            tokens = tokenizer.tokenize(text[:10000])  # Cap to prevent timeouts on huge text
            subword_time = (time.perf_counter() - start) * 1000
            subword_count = len(tokens)
        except Exception as e:
            logger.warning(f"Subword tokenizer benchmark fallback: {e}")
            # Fallback mock BPE calculation
            start = time.perf_counter()
            subword_count = int(len(word_tokens) * 1.3)
            subword_time = (time.perf_counter() - start) * 1000

        metrics["subword"] = {
            "token_count": subword_count,
            "latency_ms": round(subword_time, 4),
            "speed_tokens_per_ms": round(subword_count / (subword_time + 1e-9), 2)
        }

        return metrics

    def analyze_syntax(self, text: str) -> Dict[str, Any]:
        """Performs sentence segmentation, POS tagging, lemmatization, and parsing using spaCy."""
        result = {
            "sentences": [],
            "tokens": []
        }
        if not text or not self.nlp:
            return result

        try:
            doc = self.nlp(text[:10000])  # Analyze up to 10k characters for performance
            for sent in doc.sents:
                result["sentences"].append(sent.text.strip())

            for token in doc[:500]:  # Limit details to first 500 tokens to avoid huge JSON payloads
                result["tokens"].append({
                    "text": token.text,
                    "lemma": token.lemma_,
                    "pos": token.pos_,
                    "tag": token.tag_,
                    "dep": token.dep_,
                    "head": token.head.text
                })
        except Exception as e:
            logger.error(f"spaCy syntax analysis failed: {e}")

        return result

    def preprocess(self, text: str) -> Dict[str, Any]:
        """Runs the complete advanced NLP preprocessing pipeline."""
        t_start = time.perf_counter()
        
        unicode_normalized = self.normalize_unicode(text)
        cleaned = self.correct_ocr_noise(unicode_normalized)
        text_normalized = self.normalize_text(cleaned)
        expanded = self.expand_abbreviations(text_normalized)
        
        lang = self.detect_language(expanded)
        benchmarks = self.benchmark_tokenizers(expanded)
        syntax = self.analyze_syntax(expanded)
        
        duration = (time.perf_counter() - t_start) * 1000

        return {
            "preprocessed_text": expanded,
            "language": lang,
            "benchmarks": benchmarks,
            "sentences": syntax["sentences"],
            "tokens": syntax["tokens"],
            "latency_ms": round(duration, 2)
        }

preprocessor = LegalTextPreprocessor()
