import uuid
from sqlalchemy import Column, String, Boolean, JSON, Integer, Float, DateTime, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
from database.session import Base

class AgentRegistryModel(Base):
    __tablename__ = "agent_registry"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id = Column(String(100), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(String(1000), nullable=True)
    version = Column(String(50), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    capabilities = Column(JSON, nullable=False, default=list)
    supported_tasks = Column(JSON, nullable=False, default=list)
    input_schema = Column(JSON, nullable=False, default=dict)
    output_schema = Column(JSON, nullable=False, default=dict)
    policy = Column(JSON, nullable=False, default=dict)
    health_status = Column(String(50), nullable=False, default="HEALTHY")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint('agent_id', 'version', name='uq_agent_version'),
    )

class AgentMetricsLog(Base):
    __tablename__ = "agent_metrics_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id = Column(String(100), nullable=False, index=True)
    version = Column(String(50), nullable=False)
    success_count = Column(Integer, nullable=False, default=0)
    failure_count = Column(Integer, nullable=False, default=0)
    total_latency_ms = Column(Integer, nullable=False, default=0)
    last_failure_at = Column(DateTime(timezone=True), nullable=True)
    last_success_at = Column(DateTime(timezone=True), nullable=True)
    cpu_usage_pct = Column(Float, nullable=False, default=0.0)
    memory_usage_mb = Column(Float, nullable=False, default=0.0)

    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint('agent_id', 'version', name='uq_agent_metric_version'),
    )
