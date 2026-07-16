import uuid
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from models.document import Document
from models.document_intelligence import DocumentPage
from models.rag import RAGChunk, RAGEmbedding
from services.legal_ai.chunker import LegalDocumentChunker
from services.legal_ai.embeddings.factory import EmbeddingProviderFactory

class RAGEmbeddingPipeline:
    """RAG Ingestion and Embedding Pipeline. Manages chunk lifecycles and batch vector generation."""
    
    @staticmethod
    def index_document_rag(
        db: Session, 
        document_id: uuid.UUID, 
        chunk_strategy: str = "paragraph", 
        embedding_model: str = "MiniLM"
    ) -> int:
        # 1. Fetch document and page contents
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            raise ValueError(f"Document {document_id} not found.")

        pages = db.query(DocumentPage).filter(DocumentPage.document_id == document_id).order_by(DocumentPage.page_number.asc()).all()
        if not pages:
            return 0

        # Mark all existing active chunks for this document as "Superseded" to ensure search reproducibility
        db.query(RAGChunk).filter(
            RAGChunk.document_id == document_id,
            RAGChunk.status == "Active"
        ).update({"status": "Superseded"})
        db.commit()

        # 2. Extract chunks using selected strategy
        provider = EmbeddingProviderFactory.get_provider(embedding_model)
        chunker = LegalDocumentChunker()
        
        all_chunks = []
        for p in pages:
            meta = {
                "title": doc.title,
                "page_number": p.page_number
            }
            if chunk_strategy == "clause":
                page_chunks = chunker.chunk_by_clauses(p.text, meta)
            elif chunk_strategy == "section":
                page_chunks = chunker.chunk_by_sections(p.text, meta)
            else:
                page_chunks = chunker.chunk_by_paragraphs(p.text, meta)
            all_chunks.extend(page_chunks)

        if not all_chunks:
            return 0

        # 3. Generate embeddings in optimized batches
        texts = [c["text"] for c in all_chunks]
        embeddings = provider.get_embeddings(texts)

        # 4. Save to Database
        for chunk_data, emb in zip(all_chunks, embeddings):
            db_chunk = RAGChunk(
                document_id=document_id,
                chunk_type=chunk_data["chunk_type"],
                text=chunk_data["text"],
                page_number=chunk_data["page_number"],
                start_char=chunk_data["start_char"],
                end_char=chunk_data["end_char"],
                status="Active",
                metadata_json=chunk_data["metadata_json"],
                embedding_model=embedding_model,
                embedding_version="v1.0.0"
            )
            db.add(db_chunk)
            db.flush()  # Generate db_chunk.id

            db_emb = RAGEmbedding(
                chunk_id=db_chunk.id,
                embedding_model=embedding_model,
                vector_data=emb
            )
            db.add(db_emb)

        db.commit()

        # 5. Automatically build Knowledge Graph for the indexed document version
        from models.document import DocumentVersion
        from services.legal_ai.graph_builder import KnowledgeGraphBuilder
        import logging
        logger = logging.getLogger("redactai.legal_ai.embedding_pipeline")

        latest_version = db.query(DocumentVersion).filter(
            DocumentVersion.document_id == document_id
        ).order_by(DocumentVersion.created_at.desc()).first()

        if not latest_version:
            latest_version = DocumentVersion(
                document_id=document_id,
                version_number=1,
                storage_path=doc.storage_path,
                file_size=doc.file_size
            )
            db.add(latest_version)
            db.commit()
            db.refresh(latest_version)

        try:
            KnowledgeGraphBuilder.build_graph_for_document(db, latest_version.id)
            logger.info(f"Successfully constructed knowledge graph for version {latest_version.id}")
        except Exception as ge:
            logger.error(f"Failed to construct knowledge graph for version {latest_version.id}: {ge}")

        return len(all_chunks)

    @staticmethod
    def reindex_all_documents(db: Session, new_embedding_model: str) -> int:
        """Regenerates embeddings for all indexed documents when switching active models."""
        active_chunks = db.query(RAGChunk).filter(RAGChunk.status == "Active").all()
        if not active_chunks:
            return 0

        # Group chunk texts to batch-encode
        texts = [c.text for c in active_chunks]
        provider = EmbeddingProviderFactory.get_provider(new_embedding_model)
        new_embeddings = provider.get_embeddings(texts)

        # Update RAGChunk status to Reindexed
        db.query(RAGChunk).filter(RAGChunk.status == "Active").update({"status": "Reindexed"})
        db.commit()

        # Re-save new active chunks & embeddings
        for c, emb in zip(active_chunks, new_embeddings):
            db_chunk = RAGChunk(
                document_id=c.document_id,
                version_id=c.version_id,
                chunk_type=c.chunk_type,
                text=c.text,
                page_number=c.page_number,
                start_char=c.start_char,
                end_char=c.end_char,
                status="Active",
                metadata_json=c.metadata_json,
                embedding_model=new_embedding_model,
                embedding_version="v1.0.0"
            )
            db.add(db_chunk)
            db.flush()

            db_emb = RAGEmbedding(
                chunk_id=db_chunk.id,
                embedding_model=new_embedding_model,
                vector_data=emb
            )
            db.add(db_emb)

        db.commit()
        return len(active_chunks)
