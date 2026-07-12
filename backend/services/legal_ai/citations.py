"""Citations extraction and source mapping validator."""
import re
from typing import List, Dict, Any

class LegalCitationValidator:
    def __init__(self):
        self.citation_pattern = r"\[([^\]]+)\]"

    def extract_citations(self, text: str) -> List[str]:
        """Extract all bracketed citations from generating answer text (e.g. [DPDP Act, Section 4])."""
        matches = re.findall(self.citation_pattern, text)
        return [m.strip() for m in matches if "," in m or "Act" in m or "Guideline" in m or "Rule" in m]

    def validate_citations(self, text: str, retrieved_context: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Cross-reference extracted citations against actually retrieved knowledge chunks to prevent hallucination."""
        citations = self.extract_citations(text)
        
        validated = []
        valid_sources = {
            f"{chunk['metadata']['source'].lower()} section {str(chunk['metadata']['section_number']).lower()}": chunk
            for chunk in retrieved_context
        }
        valid_source_names = {chunk['metadata']['source'].lower() for chunk in retrieved_context}

        for cit in citations:
            cit_lower = cit.lower()
            match_found = False
            linked_chunk = None

            # Attempt soft match
            for valid_key, chunk in valid_sources.items():
                # e.g. "dpdp act section 4" in "dpdp act, section 4"
                clean_key = valid_key.replace(" ", "")
                clean_cit = cit_lower.replace(",", "").replace(" ", "")
                if clean_key in clean_cit or clean_cit in clean_key:
                    match_found = True
                    linked_chunk = chunk
                    break

            if not match_found:
                # Fallback check on source name only
                for src in valid_source_names:
                    if src in cit_lower:
                        match_found = True
                        break

            validated.append({
                "citation": cit,
                "is_hallucinated": not match_found,
                "referenced_source": linked_chunk["metadata"]["source"] if linked_chunk else "General Regulation Reference",
                "section_number": linked_chunk["metadata"]["section_number"] if linked_chunk else "Unknown"
            })

        return validated

    def validate_and_score_citations(self, text: str, retrieved_context: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Verify citations and compute structured coverage, correctness, and review flags."""
        validated = self.validate_citations(text, retrieved_context)
        total_citations = len(validated)
        
        # Calculate coverage: % of retrieved context blocks actually referenced in verified citations
        cited_doc_ids = set()
        for v in validated:
            if not v["is_hallucinated"] and v["referenced_source"] != "General Regulation Reference":
                # Find matching chunk source/section
                for rc in retrieved_context:
                    if rc["metadata"]["source"] == v["referenced_source"] and str(rc["metadata"]["section_number"]) == str(v["section_number"]):
                        cited_doc_ids.add(rc["chunk_id"])

        total_retrieved = len(retrieved_context)
        coverage = len(cited_doc_ids) / total_retrieved if total_retrieved > 0 else 0.0
        
        # Calculate correctness: % of generated citations that match retrieved sources
        correct_citations = sum(1 for v in validated if not v["is_hallucinated"])
        correctness = correct_citations / total_citations if total_citations > 0 else 1.0
        
        # Unsupported claims count: citations that are hallucinated (not backed by vector db context)
        unsupported_claims_count = sum(1 for v in validated if v["is_hallucinated"])
        
        # Determine warning and human review need
        warning = None
        human_review_recommended = False
        if correctness < 0.75 or unsupported_claims_count > 0:
            warning = "Potential hallucination or unsupported legal claims detected in the response."
            human_review_recommended = True
        elif total_citations == 0:
            warning = "No citations provided in the answer. Human review recommended to verify statement validity."
            human_review_recommended = True

        return {
            "citations": validated,
            "citation_coverage": round(coverage, 2),
            "citation_correctness": round(correctness, 2),
            "unsupported_claims_count": unsupported_claims_count,
            "warning": warning,
            "human_review_recommended": human_review_recommended
        }
