import uuid
from sqlalchemy import Column, String, Integer, Float, Boolean, Text, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
from database.session import Base


class DocumentMetadata(Base):
    """Extraction metadata for processed documents."""
    __tablename__ = "document_metadata"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, unique=True)
    file_size = Column(Integer, nullable=False)
    mime_type = Column(String(100), nullable=False)
    file_type = Column(String(50), nullable=False)  # Digital PDF, Scanned PDF, Image, Word Document
    page_count = Column(Integer, nullable=True)
    author = Column(String(255), nullable=True)
    created_date = Column(DateTime(timezone=True), nullable=True)
    modified_date = Column(DateTime(timezone=True), nullable=True)
    producer = Column(String(255), nullable=True)
    encryption_status = Column(String(50), nullable=False, default="UNENCRYPTED")
    signature_status = Column(String(50), nullable=False, default="UNSIGNED")
    language = Column(String(50), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    document = relationship("Document", backref="metadata_record")


class DocumentPage(Base):
    """Extracted text of individual document pages."""
    __tablename__ = "document_pages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    page_number = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    document = relationship("Document", backref="pages")


class DocumentBlock(Base):
    """Layout analysis segment blocks within a page."""
    __tablename__ = "document_blocks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    page_number = Column(Integer, nullable=False)
    block_type = Column(String(50), nullable=False)  # Header, Footer, Paragraph, Table, List, Image, Signature, Stamp
    text = Column(Text, nullable=True)
    coordinates = Column(JSON, nullable=True)  # [x0, y0, x1, y1]
    reading_order = Column(Integer, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    document = relationship("Document", backref="blocks")


class DocumentEntity(Base):
    """Entities detected by PII/NER processing."""
    __tablename__ = "document_entities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    page_number = Column(Integer, nullable=False)
    entity_type = Column(String(100), nullable=False, index=True)  # AADHAAR, PAN, PERSON, etc.
    value = Column(String(2000), nullable=False)
    confidence = Column(Float, nullable=False, default=0.0)
    start_char = Column(Integer, nullable=False)
    end_char = Column(Integer, nullable=False)
    bounding_box = Column(JSON, nullable=True)  # [x0, y0, x1, y1]
    risk_level = Column(String(50), nullable=False)  # LOW, MEDIUM, HIGH, CRITICAL

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    document = relationship("Document", backref="entities")


class ProcessingJob(Base):
    """Asynchronous processing jobs run on documents."""
    __tablename__ = "processing_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    job_type = Column(String(50), nullable=False, default="FULL_PIPELINE")
    status = Column(String(50), nullable=False, default="PENDING", index=True)  # PENDING, RUNNING, COMPLETED, FAILED
    celery_task_id = Column(String(255), nullable=True)
    progress = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    document = relationship("Document", backref="intelligence_jobs")


