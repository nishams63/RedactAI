import re
import unicodedata

ABBREVIATIONS = {
    r"\bu/s\b": "under section",
    r"\bsec\.?\b": "section",
    r"\bart\.?\b": "article",
    r"\bco\.?\b": "company",
    r"\bcorp\.?\b": "corporation",
    r"\bltd\.?\b": "limited",
    r"\binc\.?\b": "incorporated",
    r"\bvs\.?\b": "versus",
    r"\bipc\b": "Indian Penal Code",
    r"\bcrpc\b": "Code of Criminal Procedure",
}

def normalize_unicode(text: str) -> str:
    """Applies compatibility decomposition (NFKD) to standardise unicode characters."""
    if not text:
        return ""
    return unicodedata.normalize("NFKD", text)

def clean_ocr_noise(text: str) -> str:
    """Removes common OCR artifacts (multiple spaces, non-printable noise, strange control lines)."""
    if not text:
        return ""
    # Replace non-printable ASCII/Unicode control characters
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\xff]", "", text)
    # Condense multiple whitespace or hyphens/underscores
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[-_]{4,}", " ", text)
    return text.strip()

def expand_abbreviations(text: str) -> str:
    """Expands common legal and corporate shorthand terms based on regular expressions."""
    if not text:
        return ""
    res = text
    for pattern, replacement in ABBREVIATIONS.items():
        # Match case-insensitively but preserve case if possible (simplistic replace)
        res = re.sub(pattern, replacement, res, flags=re.IGNORECASE)
    return res

def preprocess_legal_text(text: str) -> str:
    """Applies the full preprocessing pipeline: unicode normalization, OCR cleaning, abbreviation expansion."""
    text = normalize_unicode(text)
    text = clean_ocr_noise(text)
    text = expand_abbreviations(text)
    return text
