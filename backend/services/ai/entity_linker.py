"""Module 5 - Entity Linker.

Performs entity resolution (resolving aliases, merging duplicates, tracking mentions)
and builds a canonical entity graph.
"""
import re
import logging
from typing import Dict, Any, List, Set, Tuple

logger = logging.getLogger("redactai.ai.entity_linker")

class LegalEntityLinker:
    def canonicalize_name(self, name: str, entity_type: str) -> str:
        """Cleans and standardizes name prefixes/suffixes to create a canonical lookup key."""
        if not name:
            return ""
        
        cleaned = name.strip().lower()
        cleaned = re.sub(r'[.,():;\'"]', '', cleaned)
        cleaned = re.sub(r'\s+', ' ', cleaned)
        
        if entity_type == "ORGANIZATION":
            # Strip standard company suffixes
            suffixes = [
                r"\binc\b", r"\bllc\b", r"\bltd\b", r"\blimited\b", r"\bcorp\b", 
                r"\bcorporation\b", r"\bpvt\b", r"\bprivate\b", r"\bco\b", r"\bcompany\b"
            ]
            for suff in suffixes:
                cleaned = re.sub(suff, '', cleaned)
        
        elif entity_type == "PERSON":
            # Strip standard person prefixes
            prefixes = [r"\bmr\b", r"\bms\b", r"\bmrs\b", r"\bdr\b", r"\bshri\b", r"\bsmt\b", r"\bjustice\b"]
            for pref in prefixes:
                cleaned = re.sub(pref, '', cleaned)

        return cleaned.strip()

    def check_alias(self, name1: str, name2: str, entity_type: str) -> bool:
        """Determines if name1 and name2 represent the same entity (alias resolution)."""
        key1 = self.canonicalize_name(name1, entity_type)
        key2 = self.canonicalize_name(name2, entity_type)
        
        if not key1 or not key2:
            return False
            
        if key1 == key2:
            return True
            
        # Check acronyms (e.g. TCS ↔ Tata Consultancy Services)
        if entity_type == "ORGANIZATION":
            for k1, k2 in [(key1, key2), (key2, key1)]:
                words = k2.split()
                if len(words) > 1:
                    acronym = "".join(w[0] for w in words if w)
                    if k1 == acronym:
                        return True
                        
        # Check partial subset matching for names (e.g. Amit Sharma ↔ Mr. Amit)
        if entity_type == "PERSON":
            w1 = set(key1.split())
            w2 = set(key2.split())
            # Must overlap significantly and not contradict (e.g. same last name or first name)
            if len(w1.intersection(w2)) >= 1:
                # Ensure they don't have completely different first/last names
                # For example "Amit Sharma" vs "Vijay Sharma" should not merge (Amit != Vijay)
                first_names = [key1.split()[0], key2.split()[0]]
                if len(key1.split()) > 1 and len(key2.split()) > 1:
                    if first_names[0] != first_names[1]:
                        return False
                return True
                
        return False

    def link_entities(self, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Groups mentions of entities together, resolving aliases and merging duplicates."""
        linked_groups: List[Dict[str, Any]] = []

        for ent in entities:
            ent_val = ent.get("value", "")
            ent_type = ent.get("entity_type", "PERSON")
            confidence = ent.get("confidence", 1.0)
            page = ent.get("page_number", 1)
            start_char = ent.get("start_char", 0)
            end_char = ent.get("end_char", 0)
            
            # Find an existing group this entity matches
            matched_group = None
            for group in linked_groups:
                if group["entity_type"] == ent_type:
                    # Check if matches the canonical name or any alias in the group
                    if self.check_alias(ent_val, group["canonical_name"], ent_type) or \
                       any(self.check_alias(ent_val, alias, ent_type) for alias in group["aliases"]):
                        matched_group = group
                        break
            
            mention_info = {
                "value": ent_val,
                "page_number": page,
                "start_char": start_char,
                "end_char": end_char,
                "confidence": confidence
            }
            
            if matched_group:
                # Add to existing group
                matched_group["mentions"].append(mention_info)
                matched_group["aliases"].add(ent_val)
                # Keep the longest string as the canonical representation
                if len(ent_val) > len(matched_group["canonical_name"]):
                    matched_group["canonical_name"] = ent_val
                # Update confidence to average
                matched_group["confidence"] = round(
                    sum(m["confidence"] for m in matched_group["mentions"]) / len(matched_group["mentions"]),
                    4
                )
            else:
                # Create a new canonical group
                linked_groups.append({
                    "id": f"entity_{len(linked_groups)}",
                    "canonical_name": ent_val,
                    "entity_type": ent_type,
                    "aliases": {ent_val},
                    "confidence": confidence,
                    "mentions": [mention_info]
                })

        # Format aliases set as list for JSON serialization
        for group in linked_groups:
            group["aliases"] = list(group["aliases"])

        return linked_groups

entity_linker = LegalEntityLinker()
