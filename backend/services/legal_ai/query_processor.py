import re
from typing import Dict, Any, List

class LegalQueryProcessor:
    """Enterprise RAG query pre-processor handling cleaning, classification, expansion, and metadata extraction."""

    @staticmethod
    def clean_query(query: str) -> str:
        """Removes noise, special characters, and double spaces from query text."""
        cleaned = re.sub(r"[^\w\s\-\.\,\?]", "", query)
        cleaned = re.sub(r"\s+", " ", cleaned)
        return cleaned.strip()

    @staticmethod
    def classify_query(query: str) -> str:
        """Classifies query intent into compliance, qa, threat_analysis, or search."""
        q_lower = query.lower()
        if any(w in q_lower for w in ["comply", "compliance", "violation", "breach"]):
            return "compliance"
        elif any(w in q_lower for w in ["risk", "threat", "exposure", "liability"]):
            return "threat_analysis"
        elif any(w in q_lower for w in ["search", "find", "locate", "document"]):
            return "search"
        else:
            return "qa"

    @staticmethod
    def expand_query(query: str) -> str:
        """Appends legal synonyms and expansion vocabulary terms to enhance hybrid sparse search recall."""
        q_lower = query.lower()
        expansions = []
        
        synonyms = {
            "consent": ["permission", "agreement", "authorization", "data principal assent"],
            "breach": ["data leak", "security incident", "unauthorized access", "disclosure"],
            "retention": ["storage limit", "holding period", "data deletion", "purge"],
            "penalty": ["monetary fine", "warning", "sanctions", "prosecution"],
            "notice": ["information request", "disclosure obligation", "communication"]
        }
        
        for key, syns in synonyms.items():
            if key in q_lower:
                expansions.extend(syns)
                
        if expansions:
            return f"{query} ({', '.join(expansions)})"
        return query

    @staticmethod
    def rewrite_query(query: str, history: List[Dict[str, Any]] = None) -> str:
        """Resolves reference ambiguities (e.g. pronouns like 'it', 'its', 'their') based on chat history context."""
        if not history or not query:
            return query
            
        q_lower = query.lower()
        # If the query contains pronouns refering to a previous noun, replace it
        pronouns = ["what is its penalty", "how does it comply", "explain their rules"]
        has_pronoun = any(p in q_lower for p in [" it ", " its ", " their ", " it?", " its?"])
        
        if has_pronoun:
            # Find the last subject discussed in chat history
            last_subject = None
            for msg in reversed(history):
                text = msg.get("text", "").lower()
                if "dpdp" in text:
                    last_subject = "DPDP Act"
                    break
                elif "rbi" in text:
                    last_subject = "RBI KYC Guidelines"
                    break
                elif "uidai" in text:
                    last_subject = "UIDAI circular"
                    break
                    
            if last_subject:
                # Replace simple pronouns with the subject noun
                rewritten = query.replace(" its ", f" {last_subject}'s ").replace(" it ", f" {last_subject} ")
                return rewritten
                
        return query

    def process_query(self, query: str, history: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Runs the complete enterprise query pipeline, returning cleaned, classified query and extracted filters."""
        cleaned = self.clean_query(query)
        rewritten = self.rewrite_query(cleaned, history)
        classification = self.classify_query(rewritten)
        expanded = self.expand_query(rewritten)
        
        # Metadata filters extraction (dates, departments, clients)
        filters = {}
        
        # 1. Date filters
        year_match = re.search(r"\b(202[0-9]|199[0-9])\b", query)
        if year_match:
            filters["year"] = int(year_match.group(1))
            
        # 2. Department filter
        dept_match = re.search(r"\b(legal|hr|compliance|security|finance|it)\b", query.lower())
        if dept_match:
            filters["department"] = dept_match.group(1).title()
            
        # 3. Client filter
        client_match = re.search(r"\bclient\s+([A-Za-z0-9]+)\b", query.lower())
        if client_match:
            filters["client"] = client_match.group(1).upper()

        return {
            "original_query": query,
            "cleaned_query": cleaned,
            "rewritten_query": rewritten,
            "expanded_query": expanded,
            "intent_classification": classification,
            "extracted_metadata_filters": filters
        }
