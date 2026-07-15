"""Module 2 - Legal Document Structure Analyzer.

Classifies layout blocks into Title, Header, Footer, Section/Clause, List, Table, Signature, Paragraph, Stamp.
"""
import re
import logging
from typing import Dict, Any, List

logger = logging.getLogger("redactai.ai.structure_analyzer")

class LegalStructureAnalyzer:
    def classify_block(self, text: str, page_num: int, coords: List[float], page_height: float) -> str:
        """Classifies a document block's text and coordinates into legal structure types."""
        if not text:
            return "Paragraph"
        
        cleaned = text.strip()
        lower_text = cleaned.lower()
        y0, y1 = coords[1], coords[3]
        
        # 1. Title (Only on page 1, near the top, usually centered and uppercase/bold)
        if page_num == 1 and y0 < 200:
            # Check if all caps or starts with typical title terms
            if cleaned.isupper() and len(cleaned) > 10 and len(cleaned) < 150:
                return "Title"
            if "agreement" in lower_text or "contract" in lower_text or "deed" in lower_text or "memorandum" in lower_text:
                if len(cleaned) < 100:
                    return "Title"

        # 2. Header & Footer (Vertical position boundaries)
        if page_height > 0:
            if y0 < 50:
                return "Header"
            if y1 > (page_height - 50):
                return "Footer"

        # 3. Signature Block
        signature_keywords = [
            "signed by", "witness", "signature", "signatory", "executed by", 
            "for and on behalf of", "authorized signatory", "in the presence of"
        ]
        if any(kw in lower_text for kw in signature_keywords):
            return "Signature Area"

        # 4. Stamp / Seal
        stamp_keywords = ["seal", "stamp", "receipt", "notary", "frd", "certified true copy"]
        if any(kw in lower_text for kw in stamp_keywords) and len(cleaned) < 50:
            return "Stamp"

        # 5. Section / Clause Headers
        # Matches e.g. "Section 1", "Clause 2.3", "Article IV"
        section_patterns = [
            r"^(?:section|clause|article|para|paragraph)\s+\d+(?:\.\d+)*\b",
            r"^(?:section|clause|article)\s+[ivxldcm]+\b",
        ]
        if any(re.match(pat, cleaned, re.IGNORECASE) for pat in section_patterns):
            return "Section"

        # Check for uppercase headings (like "1. DEFINITIONS" or "CONFIDENTIALITY")
        if cleaned.isupper():
            if re.match(r"^\d+\.\s+[A-Z\s]{4,40}$", cleaned) or re.match(r"^[A-Z\s]{5,50}$", cleaned):
                return "Section"

        # 6. Numbered Lists
        # Matches e.g. "1.", "(a)", "ii)", "a."
        list_patterns = [
            r"^(?:\d+|\w)\.\s+",
            r"^\(\w\)\s+",
            r"^[ivxldcm]+\.\s+",
            r"^(?:\d+|\w)\)\s+"
        ]
        if any(re.match(pat, cleaned, re.IGNORECASE) for pat in list_patterns) or cleaned.startswith(("•", "-", "*")):
            return "List"

        # 7. Tables
        # Detect rows containing multiple aligned text columns (e.g. separated by tabs or multiple spaces)
        if "\t" in cleaned or "   " in cleaned:
            lines = [l.strip() for l in cleaned.split("\n") if l.strip()]
            multi_col_lines = 0
            for line in lines:
                if len(re.split(r'\t|\s{2,}', line)) > 1:
                    multi_col_lines += 1
            if len(lines) > 0 and (multi_col_lines / len(lines)) > 0.5:
                return "Table"

        # Default fallback
        return "Paragraph"

    def analyze_structure(self, blocks: List[Dict[str, Any]], page_height: float = 842.0) -> List[Dict[str, Any]]:
        """Process a list of layout blocks and append classification labels."""
        structured_blocks = []
        for idx, block in enumerate(blocks):
            label = self.classify_block(
                text=block.get("text", ""),
                page_num=block.get("page_number", 1),
                coords=block.get("coordinates", [0, 0, 0, 0]),
                page_height=page_height
            )
            block_copy = dict(block)
            block_copy["block_type"] = label
            structured_blocks.append(block_copy)
        return structured_blocks

structure_analyzer = LegalStructureAnalyzer()
