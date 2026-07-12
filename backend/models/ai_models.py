"""
AI Placeholder Models — Sprint 1
These tables are created now to establish the schema for future AI modules.
No AI logic is implemented in Sprint 1.
"""
import uuid
from sqlalchemy import Column, String, Integer, Float, Boolean, Text, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
from database.session import Base


class AIModel(Base):
    """Registry of AI/ML models used for document processing."""
    __tablename__ = "models"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)           # e.g., LayoutLM, spaCy-Legal, Redact-v1
    version = Column(String(100), nullable=False)
    type = Column(String(50), nullable=False, index=True) # OCR, NER, REDACTION
    status = Column(String(50), nullable=False, default="ACTIVE")  # ACTIVE, DEPRECATED
    parameters = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class DetectedEntity(Base):
    """Entities detected by NER/PII models within a document."""
    __tablename__ = "detected_entities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    entity_type = Column(String(100), nullable=False, index=True)  # AADHAAR, PAN, PERSON, ORG, etc.
    text = Column(String(2000), nullable=False)
    start_char = Column(Integer, nullable=False)
    end_char = Column(Integer, nullable=False)
    confidence = Column(Float, nullable=False, default=0.0)
    is_redacted = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    document = relationship("Document", backref="detected_entities")


class Redaction(Base):
    """Records of redactions applied to detected entities."""
    __tablename__ = "redactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    detected_entity_id = Column(UUID(as_uuid=True), ForeignKey("detected_entities.id", ondelete="SET NULL"), nullable=True)
    redaction_type = Column(String(50), nullable=False)          # MASK, BLUR, REPLACE
    replacement_text = Column(String(500), nullable=True)
    bounding_box = Column(JSON, nullable=True)                  # Coordinate rectangles for visual redact
    status = Column(String(50), nullable=False, default="PENDING")  # PENDING, APPLIED, SKIPPED

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    document = relationship("Document", backref="redactions")
    detected_entity = relationship("DetectedEntity", backref="redactions")


class ComplianceResult(Base):
    """Results from compliance rule checks on a document."""
    __tablename__ = "compliance_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    rule_name = Column(String(255), nullable=False)
    severity = Column(String(50), nullable=False)  # HIGH, MEDIUM, LOW
    passed = Column(Boolean, nullable=False)
    details = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    document = relationship("Document", backref="compliance_results")


class ProcessingLog(Base):
    """Structured logs for each stage of document processing pipeline."""
    __tablename__ = "processing_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    stage = Column(String(50), nullable=False, index=True)  # OCR, NER, COMPLIANCE, etc.
    log_level = Column(String(20), nullable=False)           # INFO, WARNING, ERROR
    message = Column(Text, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    document = relationship("Document", backref="processing_logs")


class HumanReview(Base):
    """Stores human reviewer decisions for model feedback and correction."""
    __tablename__ = "human_reviews"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    category = Column(String(100), nullable=False)  # e.g., "COMPLIANCE", "CLASSIFICATION", "REDACTION"
    ai_recommendation = Column(JSON, nullable=True)
    reviewer_decision = Column(String(50), nullable=False)  # e.g., "APPROVED", "OVERRIDDEN"
    reviewer_comments = Column(Text, nullable=True)
    final_decision = Column(JSON, nullable=True)
    reviewed_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    document = relationship("Document", backref="human_reviews")
    user = relationship("User", backref="human_reviews")


class PromptRegistry(Base):
    """Registry tracking versioned RAG prompts and template history."""
    __tablename__ = "prompt_registry"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    prompt_id = Column(String(255), nullable=False)  # e.g., "rag_qa_template"
    version = Column(String(50), nullable=False)     # e.g., "v1.0.0"
    template = Column(Text, nullable=False)
    associated_model = Column(String(255), nullable=False)
    kb_version = Column(String(50), nullable=False)
    performance_metrics = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class BenchmarkQuestion(Base):
    """Dataset of legal QA questions used for quality benchmarking."""
    __tablename__ = "benchmark_questions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    question = Column(Text, nullable=False)
    expected_answer = Column(Text, nullable=False)
    expected_citations = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class BenchmarkRun(Base):
    """Immutable record of validation quality benchmark runs."""
    __tablename__ = "benchmark_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    prompt_version = Column(String(50), nullable=False)
    model_version = Column(String(100), nullable=False)
    kb_version = Column(String(50), nullable=False)
    embedding_version = Column(String(50), nullable=False)

    # Metrics
    retrieval_metrics = Column(JSON, nullable=False)  # Recall@5, Recall@10, Precision@5, MRR
    citation_metrics = Column(JSON, nullable=False)   # Coverage, Correctness, Unsupported
    latency = Column(Float, nullable=False)            # Avg latency ms
    confidence_calibration = Column(JSON, nullable=False)
    regression_status = Column(String(50), nullable=False)  # IMPROVED, REGRESSED, UNCHANGED

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class PerformanceProfile(Base):
    """Timings and resource tracking of individual request pipeline runs."""
    __tablename__ = "performance_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_path = Column(String(500), nullable=False)
    method = Column(String(10), nullable=False)
    status_code = Column(Integer, nullable=False)

    # Dictionary containing stage latencies
    stages = Column(JSON, nullable=False)  # Upload, Validation, OCR, NER, PII, RAG, SLM, etc.
    total_latency = Column(Float, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class PerformanceBenchmark(Base):
    """Execution results for automated pipeline load tests."""
    __tablename__ = "performance_benchmarks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    concurrency = Column(Integer, nullable=False)
    throughput = Column(Float, nullable=False)  # Requests per second
    avg_latency = Column(Float, nullable=False)
    peak_latency = Column(Float, nullable=False)
    failure_rate = Column(Float, nullable=False)
    cpu_util = Column(Float, nullable=False)
    ram_util = Column(Float, nullable=False)
    cache_stats = Column(JSON, nullable=False)

    improvement_report = Column(JSON, nullable=True)
    regression_report = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class QueueMetric(Base):
    """Queue parameters including length, wait times, and job failures."""
    __tablename__ = "queue_metrics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    queue_length = Column(Integer, nullable=False)
    wait_time = Column(Float, nullable=False)      # Average queue wait time in ms
    worker_util = Column(Float, nullable=False)    # Worker utilization (0.0 to 1.0)
    retry_count = Column(Integer, nullable=False)
    failed_jobs = Column(Integer, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class UserSession(Base):
    """Tracks active user sessions, token rotation identifiers, and revocation gates."""
    __tablename__ = "user_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    session_key = Column(String(512), unique=True, nullable=False, index=True)
    ip_address = Column(String(100), nullable=True)
    user_agent = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    last_active_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class LoginAttempt(Base):
    """Tracks brute-force metrics, locations, and lockout blocks."""
    __tablename__ = "login_attempts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), nullable=False, index=True)
    ip_address = Column(String(100), nullable=True)
    user_agent = Column(String(500), nullable=True)
    status = Column(String(50), nullable=False)  # SUCCESS, FAILED, LOCKED_OUT
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class PasswordHistory(Base):
    """Prevents password reuse within the last 5 cycles."""
    __tablename__ = "password_histories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class AuditLog(Base):
    """Immutable log of critical system operations and administrative tasks."""
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=True)
    user_email = Column(String(255), nullable=True)
    action = Column(String(100), nullable=False, index=True)
    resource = Column(String(500), nullable=True)
    result = Column(String(50), nullable=False)  # SUCCESS, FAILED
    ip_address = Column(String(100), nullable=True)
    user_agent = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class SecurityAlert(Base):
    """Telemetry flags for high-risk operations and suspicious events."""
    __tablename__ = "security_alerts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type = Column(String(100), nullable=False, index=True) # FAILED_LOGINS_LIMIT, PERMISSION_VIOLATION, etc.
    severity = Column(String(50), nullable=False)  # LOW, MEDIUM, HIGH, CRITICAL
    description = Column(Text, nullable=False)
    details = Column(JSON, nullable=True)
    is_resolved = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
