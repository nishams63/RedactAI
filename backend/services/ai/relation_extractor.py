"""Module 4 - Relation Extractor.

Extracts semantic relationships between entities (Person ↔ Organization, Organization ↔ Address, etc.)
and generates graph visualization data.
"""
import re
import logging
from typing import Dict, Any, List, Set, Tuple

logger = logging.getLogger("redactai.ai.relation_extractor")

class LegalRelationExtractor:
    def __init__(self):
        pass

    def extract_relations(self, text: str, entities: List[Dict[str, Any]], clauses: List[Dict[str, Any]] = None, compliance_result: Dict[str, Any] = None) -> Dict[str, Any]:
        """Extracts relations between entities and documents, returning nodes and edges for graph visualization."""
        nodes = []
        edges = []
        
        node_ids = set()
        
        def add_node(nid: str, label: str, ntype: str):
            if nid not in node_ids:
                nodes.append({"id": nid, "label": label, "type": ntype})
                node_ids.add(nid)
                
        def add_edge(source: str, target: str, rel_type: str):
            # Avoid duplicate edges
            edge_exists = any(
                e["source"] == source and e["target"] == target and e["relation"] == rel_type
                for e in edges
            )
            if not edge_exists and source in node_ids and target in node_ids:
                edges.append({"source": source, "target": target, "relation": rel_type})

        # Add base Contract node
        contract_node_id = "contract_main"
        add_node(contract_node_id, "Legal Agreement", "CONTRACT")

        # Group entities by type
        persons = [e for e in entities if e.get("entity_type") == "PERSON"]
        orgs = [e for e in entities if e.get("entity_type") == "ORGANIZATION"]
        addresses = [e for e in entities if e.get("entity_type") == "ADDRESS"]
        phones = [e for e in entities if e.get("entity_type") == "PHONE"]
        emails = [e for e in entities if e.get("entity_type") == "EMAIL"]

        # Add all entity nodes
        for idx, p in enumerate(persons):
            add_node(f"person_{idx}", p["value"], "PERSON")
        for idx, o in enumerate(orgs):
            add_node(f"org_{idx}", o["value"], "ORGANIZATION")
        for idx, a in enumerate(addresses):
            add_node(f"address_{idx}", a["value"][:30] + "...", "ADDRESS")
        for idx, ph in enumerate(phones):
            add_node(f"phone_{idx}", ph["value"], "PHONE")
        for idx, em in enumerate(emails):
            add_node(f"email_{idx}", em["value"], "EMAIL")

        # 1. Person ↔ Organization
        # If a person and org are mentioned in close proximity, check for representation or employment words
        for p_idx, p in enumerate(persons):
            p_val = p["value"]
            for o_idx, o in enumerate(orgs):
                o_val = o["value"]
                
                # Check if they are mentioned near each other in the text
                p_start = p.get("start_char", 0)
                o_start = o.get("start_char", 0)
                distance = abs(p_start - o_start)
                
                if distance < 150:
                    span = text[min(p_start, o_start):max(p_start, o_start)]
                    lower_span = span.lower()
                    
                    relation = "ASSOCIATED_WITH"
                    if any(kw in lower_span for kw in ["represent", "on behalf of", "signatory of", "signatory for", "director", "manager"]):
                        relation = "REPRESENTS"
                    elif any(kw in lower_span for kw in ["employee", "employed by", "employment", "staff"]):
                        relation = "EMPLOYED_BY"
                        
                    add_edge(f"person_{p_idx}", f"org_{o_idx}", relation)

        # 2. Organization ↔ Address
        # Link address to its corresponding organization
        for o_idx, o in enumerate(orgs):
            o_start = o.get("start_char", 0)
            for a_idx, a in enumerate(addresses):
                a_start = a.get("start_char", 0)
                distance = abs(o_start - a_start)
                if distance < 250:
                    add_edge(f"org_{o_idx}", f"address_{a_idx}", "LOCATED_AT")

        # 3. Person ↔ Phone & Email
        # Link contact info to the person
        for p_idx, p in enumerate(persons):
            p_start = p.get("start_char", 0)
            for ph_idx, ph in enumerate(phones):
                ph_start = ph.get("start_char", 0)
                if abs(p_start - ph_start) < 200:
                    add_edge(f"person_{p_idx}", f"phone_{ph_idx}", "CONTACTS_AT")
            for em_idx, em in enumerate(emails):
                em_start = em.get("start_char", 0)
                if abs(p_start - em_start) < 200:
                    add_edge(f"person_{p_idx}", f"email_{em_idx}", "EMAILS_AT")

        # 4. Contract ↔ Parties (Signatories)
        # Link first few detected organizations and persons as contracting parties
        for o_idx in range(min(len(orgs), 3)):
            add_edge(contract_node_id, f"org_{o_idx}", "PARTY_TO")
        for p_idx in range(min(len(persons), 3)):
            # If the person doesn't represent an org that is already a party, link them directly
            is_representative = any(
                e["source"] == f"person_{p_idx}" and e["relation"] == "REPRESENTS"
                for e in edges
            )
            if not is_representative:
                add_edge(contract_node_id, f"person_{p_idx}", "PARTY_TO")

        # 5. Clause ↔ Risk (if clauses are analyzed)
        if clauses:
            for idx, clause in enumerate(clauses[:5]):  # Process top 5 clauses to avoid clutter
                clause_node_id = f"clause_{idx}"
                clause_title = clause.get("clause_type", "General")
                add_node(clause_node_id, clause_title, "CLAUSE")
                add_edge(contract_node_id, clause_node_id, "CONTAINS_CLAUSE")
                
                # Check for risk node
                risk_lvl = clause.get("risk_level", "LOW")
                if risk_lvl in ["MEDIUM", "HIGH", "CRITICAL"]:
                    risk_node_id = f"risk_{risk_lvl.lower()}"
                    add_node(risk_node_id, f"{risk_lvl} Risk", "RISK")
                    add_edge(clause_node_id, risk_node_id, "HAS_RISK")

        # 6. Document ↔ Compliance
        if compliance_result:
            status_label = compliance_result.get("compliance_status", "COMPLIANT")
            compliance_node_id = "compliance_node"
            add_node(compliance_node_id, status_label, "COMPLIANCE")
            add_edge(contract_node_id, compliance_node_id, "COMPLIANCE_STATUS")
            
            # Link violations
            for idx, violation in enumerate(compliance_result.get("detected_violations", [])):
                violation_node_id = f"violation_{idx}"
                add_node(violation_node_id, violation.get("rule", "Violation"), "VIOLATION")
                add_edge(compliance_node_id, violation_node_id, "VIOLATES")

        return {"nodes": nodes, "edges": edges}

relation_extractor = LegalRelationExtractor()
