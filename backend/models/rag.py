import uuid
from sqlalchemy import Column, String, Integer, Float, ForeignKey, DateTime, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
from database.session import Base

class RAGChunk(Base):
    __tablename__ = "rag_chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    version_id = Column(UUID(as_uuid=True), ForeignKey("document_versions.id", ondelete="SET NULL"), nullable=True)
    chunk_type = Column(String(50), nullable=False)  # paragraph, clause, section
    text = Column(Text, nullable=False)
    page_number = Column(Integer, nullable=False)
    start_char = Column(Integer, nullable=True)
    end_char = Column(Integer, nullable=True)
    status = Column(String(50), nullable=False, default="Active")  # Active, Superseded, Deleted, Reindexed
    metadata_json = Column(JSON, nullable=True)  # custom offsets, hierarchy, etc.
    embedding_model = Column(String(100), nullable=True)
    embedding_version = Column(String(50), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    document = relationship("Document", backref="rag_chunks")

class RAGEmbedding(Base):
    __tablename__ = "rag_embeddings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chunk_id = Column(UUID(as_uuid=True), ForeignKey("rag_chunks.id", ondelete="CASCADE"), nullable=False, unique=True)
    embedding_model = Column(String(100), nullable=False)
    vector_data = Column(JSON, nullable=False)  # stored as JSON array

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    chunk = relationship("RAGChunk", backref="embeddings")

class RAGRelationship(Base):
    __tablename__ = "rag_relationships"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_chunk_id = Column(UUID(as_uuid=True), ForeignKey("rag_chunks.id", ondelete="CASCADE"), nullable=False)
    target_chunk_id = Column(UUID(as_uuid=True), ForeignKey("rag_chunks.id", ondelete="CASCADE"), nullable=False)
    relationship_type = Column(String(50), nullable=False)  # parent_child, cross_reference, version_overlap

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class RAGSearchAnalytics(Base):
    __tablename__ = "rag_search_analytics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    query = Column(String(1000), nullable=False)
    cleaned_query = Column(String(1000), nullable=True)
    classification = Column(String(100), nullable=True)
    latency_ms = Column(Float, nullable=False)
    token_usage = Column(Integer, nullable=True)
    feedback_rating = Column(Integer, nullable=True)  # 1-5 rating
    conversation_id = Column(UUID(as_uuid=True), nullable=True)
    message_id = Column(UUID(as_uuid=True), nullable=True)
    parent_message_id = Column(UUID(as_uuid=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
