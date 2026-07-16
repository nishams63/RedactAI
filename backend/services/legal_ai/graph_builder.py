import uuid
import logging
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from models.document import Document, DocumentVersion
from models.document_intelligence import DocumentPage, DocumentEntity
from models.graph import GraphNode, GraphEdge
from services.ai.relation_extractor import LegalRelationExtractor
from services.ai.entity_linker import LegalEntityLinker
from services.legal_ai.embeddings.factory import EmbeddingProviderFactory

logger = logging.getLogger("redactai.legal_ai.graph_builder")

class KnowledgeGraphBuilder:
    @staticmethod
    def build_graph_for_document(db: Session, document_version_id: uuid.UUID) -> int:
        """Constructs and persists a versioned Knowledge Graph for a document version."""
        doc_version = db.query(DocumentVersion).filter(DocumentVersion.id == document_version_id).first()
        if not doc_version:
            raise ValueError(f"Document version {document_version_id} not found.")
            
        doc = db.query(Document).filter(Document.id == doc_version.document_id).first()
        if not doc:
            raise ValueError(f"Parent document {doc_version.document_id} not found.")
            
        org_id = doc.organization_id

        # Clean existing graph version nodes and edges to support re-indexing
        db.query(GraphNode).filter(GraphNode.document_version_id == document_version_id).delete()
        db.query(GraphEdge).filter(GraphEdge.document_version_id == document_version_id).delete()
        db.commit()

        pages = db.query(DocumentPage).filter(DocumentPage.document_id == doc.id).order_by(DocumentPage.page_number.asc()).all()
        if not pages:
            return 0

        relation_extractor = LegalRelationExtractor()
        linker = LegalEntityLinker()
        provider = EmbeddingProviderFactory.get_provider("MiniLM")

        node_map: Dict[tuple, GraphNode] = {}
        
        def get_or_create_node(name: str, node_type: str, page_number: int, confidence: float) -> GraphNode:
            canonical = linker.canonicalize_name(name, node_type) or name.strip().lower()
            key = (canonical, node_type)
            if key in node_map:
                return node_map[key]

            # Generate semantic vector embedding for the node
            embedding_vector = provider.get_embedding(name)

            properties = {
                "originating_document_id": str(doc.id),
                "document_version_id": str(document_version_id),
                "page_number": page_number,
                "extraction_model": "LegalBERT + EntityLinker",
                "extraction_confidence": confidence,
                "canonical_name": canonical
            }

            db_node = GraphNode(
                organization_id=org_id,
                document_version_id=document_version_id,
                node_type=node_type,
                label=name,
                properties=properties,
                embedding_vector=embedding_vector
            )
            db.add(db_node)
            db.flush()
            node_map[key] = db_node
            return db_node

        edges_to_create = []

        # Root Document Node
        doc_node = get_or_create_node(doc.title, "Document", 1, 1.0)

        for p in pages:
            # Paragraph nodes
            p_node = get_or_create_node(
                name=f"Paragraph Page {p.page_number}", 
                node_type="Paragraph", 
                page_number=p.page_number, 
                confidence=1.0
            )
            # Re-read/store paragraph text
            p_node.properties = {**p_node.properties, "text": p.text}
            
            edges_to_create.append({
                "source": p_node, "target": doc_node, "rel": "BELONGS_TO"
            })

            page_entities = db.query(DocumentEntity).filter(
                DocumentEntity.document_id == doc.id,
                DocumentEntity.page_number == p.page_number
            ).all()

            raw_entities = [
                {
                    "entity_type": e.entity_type,
                    "value": e.value,
                    "confidence": e.confidence,
                    "start_char": e.start_char,
                    "end_char": e.end_char
                }
                for e in page_entities
            ]

            extracted = relation_extractor.extract_relations(p.text, raw_entities)
            
            local_node_id_map = {}
            for item in extracted.get("nodes", []):
                local_id = item["id"]
                label = item["label"]
                ntype = item["type"]
                
                matching_ent = next((e for e in page_entities if e.value == label), None)
                conf = matching_ent.confidence if matching_ent else 0.8
                
                db_ent_node = get_or_create_node(label, ntype, p.page_number, conf)
                local_node_id_map[local_id] = db_ent_node
                
                edges_to_create.append({
                    "source": db_ent_node, "target": p_node, "rel": "PART_OF"
                })

            for edge in extracted.get("edges", []):
                src_local = edge["source"]
                tgt_local = edge["target"]
                rel = edge["relation"]
                
                if src_local in local_node_id_map and tgt_local in local_node_id_map:
                    edges_to_create.append({
                        "source": local_node_id_map[src_local],
                        "target": local_node_id_map[tgt_local],
                        "rel": rel
                    })

        saved_edges_set = set()
        for edge_spec in edges_to_create:
            src = edge_spec["source"]
            tgt = edge_spec["target"]
            rel = edge_spec["rel"]
            
            edge_key = (src.id, tgt.id, rel)
            if edge_key in saved_edges_set:
                continue
                
            db_edge = GraphEdge(
                organization_id=org_id,
                document_version_id=document_version_id,
                source_node_id=src.id,
                target_node_id=tgt.id,
                relationship_type=rel,
                weight=1.0,
                confidence_score=0.85,
                source_module="nlp_pipeline",
                extraction_algorithm="RelationExtractor",
                verification_status="PENDING",
                properties={"source_label": src.label, "target_label": tgt.label}
            )
            db.add(db_edge)
            saved_edges_set.add(edge_key)

        db.commit()
        return len(node_map)
