import uuid
from sqlalchemy import Column, String, Integer, Float, Boolean, Text, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
from database.session import Base

class GraphNode(Base):
    __tablename__ = "graph_nodes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    document_version_id = Column(UUID(as_uuid=True), ForeignKey("document_versions.id", ondelete="CASCADE"), nullable=False, index=True)
    node_type = Column(String(50), nullable=False)
    label = Column(String(255), nullable=False)
    properties = Column(JSON, nullable=False, default=dict)
    embedding_vector = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    organization = relationship("Organization", backref="graph_nodes")
    document_version = relationship("DocumentVersion", backref="graph_nodes")

class GraphEdge(Base):
    __tablename__ = "graph_edges"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    document_version_id = Column(UUID(as_uuid=True), ForeignKey("document_versions.id", ondelete="CASCADE"), nullable=False, index=True)
    source_node_id = Column(UUID(as_uuid=True), ForeignKey("graph_nodes.id", ondelete="CASCADE"), nullable=False, index=True)
    target_node_id = Column(UUID(as_uuid=True), ForeignKey("graph_nodes.id", ondelete="CASCADE"), nullable=False, index=True)
    relationship_type = Column(String(50), nullable=False)
    weight = Column(Float, nullable=False, default=1.0)
    confidence_score = Column(Float, nullable=False, default=1.0)
    source_module = Column(String(50), nullable=False)
    extraction_algorithm = Column(String(50), nullable=False)
    verification_status = Column(String(50), nullable=False, default="PENDING") # PENDING, APPROVED, REJECTED
    properties = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    organization = relationship("Organization", backref="graph_edges")
    document_version = relationship("DocumentVersion", backref="graph_edges")
    source_node = relationship("GraphNode", foreign_keys=[source_node_id], backref="outgoing_edges")
    target_node = relationship("GraphNode", foreign_keys=[target_node_id], backref="incoming_edges")
