"""Module 7 - Duplicate Detector.

Detects near-duplicate clauses inside a document, near-duplicate documents in an organization,
and clusters similar documents using scikit-learn.
"""
import uuid
import logging
import numpy as np
from typing import Dict, Any, List, Tuple
from sqlalchemy.orm import Session
from services.legal_ai.embedder import LocalSentenceEmbedder
from models.document import Document
from models.document_intelligence import DocumentPage

logger = logging.getLogger("redactai.ai.duplicate_detector")

class LegalDuplicateDetector:
    def __init__(self):
        self.embedder = LocalSentenceEmbedder()

    def find_duplicate_clauses(self, blocks: List[Dict[str, Any]], threshold: float = 0.85) -> List[Dict[str, Any]]:
        """Identifies duplicate or near-duplicate text blocks/clauses within a document."""
        duplicates = []
        if not blocks or len(blocks) < 2:
            return duplicates

        valid_blocks = [b for b in blocks if b.get("text") and len(b["text"].strip()) > 30]
        if len(valid_blocks) < 2:
            return duplicates

        texts = [b["text"].strip() for b in valid_blocks]
        try:
            embeddings = self.embedder.get_embeddings(texts)
            embeddings_matrix = np.array(embeddings)
            
            # Compute self-similarity matrix
            norms = np.linalg.norm(embeddings_matrix, axis=1)
            similarity = np.dot(embeddings_matrix, embeddings_matrix.T) / (np.outer(norms, norms) + 1e-9)
            
            # Find pairs above threshold (only upper triangle to avoid duplicates)
            n = len(valid_blocks)
            for i in range(n):
                for j in range(i + 1, n):
                    score = float(similarity[i, j])
                    if score >= threshold:
                        duplicates.append({
                            "clause_1": {
                                "page_number": valid_blocks[i].get("page_number", 1),
                                "block_type": valid_blocks[i].get("block_type", "Paragraph"),
                                "text": texts[i][:150] + "..."
                            },
                            "clause_2": {
                                "page_number": valid_blocks[j].get("page_number", 1),
                                "block_type": valid_blocks[j].get("block_type", "Paragraph"),
                                "text": texts[j][:150] + "..."
                            },
                            "similarity_score": round(score, 4)
                        })
        except Exception as e:
            logger.error(f"Internal duplicate clause detection failed: {e}")
            
        return duplicates

    def _get_document_embedding(self, doc_id: uuid.UUID, db: Session) -> np.ndarray:
        """Retrieves and computes average pooled embedding representing the whole document."""
        pages = db.query(DocumentPage).filter(DocumentPage.document_id == doc_id).order_by(DocumentPage.page_number.asc()).all()
        if not pages:
            return np.zeros(384)
            
        page_texts = [p.text for p in pages if p.text and p.text.strip()]
        if not page_texts:
            return np.zeros(384)

        # Retrieve embeddings and return average vector
        embeddings = self.embedder.get_embeddings(page_texts)
        return np.mean(embeddings, axis=0)

    def find_near_duplicate_documents(self, current_doc_id: uuid.UUID, organization_id: uuid.UUID, db: Session, threshold: float = 0.70) -> List[Dict[str, Any]]:
        """Finds near-duplicate documents within the same organization."""
        results = []
        try:
            curr_emb = self._get_document_embedding(current_doc_id, db)
            if np.linalg.norm(curr_emb) == 0:
                return results

            # Fetch all other processed documents in organization
            docs = db.query(Document).filter(
                Document.organization_id == organization_id,
                Document.id != current_doc_id,
                Document.status == "Processed"
            ).all()

            for doc in docs:
                doc_emb = self._get_document_embedding(doc.id, db)
                if np.linalg.norm(doc_emb) == 0:
                    continue
                
                # Compute cosine similarity
                score = np.dot(curr_emb, doc_emb) / (np.linalg.norm(curr_emb) * np.linalg.norm(doc_emb) + 1e-9)
                score = float(score)
                if score >= threshold:
                    results.append({
                        "document_id": str(doc.id),
                        "title": doc.title,
                        "original_filename": doc.original_filename,
                        "similarity_score": round(score, 4)
                    })
            
            # Sort by similarity score descending
            results.sort(key=lambda x: x["similarity_score"], reverse=True)
        except Exception as e:
            logger.error(f"Failed to find duplicate documents: {e}")
            
        return results

    def cluster_documents(self, organization_id: uuid.UUID, db: Session) -> List[Dict[str, Any]]:
        """Groups all organization documents into similarity clusters using Agglomerative Clustering."""
        clusters_list = []
        try:
            docs = db.query(Document).filter(
                Document.organization_id == organization_id,
                Document.status == "Processed"
            ).all()

            if len(docs) < 2:
                # Too few documents to cluster
                return [{"cluster_id": 0, "documents": [{"id": str(d.id), "title": d.title} for d in docs]}]

            doc_embeddings = []
            valid_docs = []
            for doc in docs:
                emb = self._get_document_embedding(doc.id, db)
                if np.linalg.norm(emb) > 0:
                    doc_embeddings.append(emb)
                    valid_docs.append(doc)

            if len(doc_embeddings) < 2:
                return [{"cluster_id": 0, "documents": [{"id": str(d.id), "title": d.title} for d in valid_docs]}]

            X = np.array(doc_embeddings)
            
            # Run Agglomerative Clustering
            from sklearn.cluster import AgglomerativeClustering
            # Max clusters caps at half the documents number
            n_clusters = max(2, len(valid_docs) // 2)
            clustering = AgglomerativeClustering(n_clusters=n_clusters, metric="cosine", linkage="average")
            labels = clustering.fit_predict(X)
            
            # Group docs by labels
            groups = {}
            for label, doc in zip(labels, valid_docs):
                label_id = int(label)
                if label_id not in groups:
                    groups[label_id] = []
                groups[label_id].append({
                    "id": str(doc.id),
                    "title": doc.title,
                    "filename": doc.original_filename
                })
                
            for label_id, group in groups.items():
                clusters_list.append({
                    "cluster_id": label_id,
                    "documents": group
                })
        except Exception as e:
            logger.error(f"Clustering failed: {e}")
            # Fallback single group
            clusters_list = [{"cluster_id": 0, "documents": []}]

        return clusters_list

duplicate_detector = LegalDuplicateDetector()
