"""Pydantic schemas for document operations."""
from datetime import datetime
from uuid import UUID
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field


class DocumentResponse(BaseModel):
    id: UUID
    title: str
    original_filename: str
    file_size: int
    mime_type: str
    owner_id: UUID
    organization_id: UUID
    status: str
    storage_path: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentListResponse(BaseModel):
    documents: list[DocumentResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class DocumentUploadResponse(BaseModel):
    document: DocumentResponse
    message: str


# ─── Document Intelligence Sub-schemas ─────────────────────────────────
class DocumentMetadataSchema(BaseModel):
    file_size: int
    mime_type: str
    file_type: str
    page_count: Optional[int] = None
    author: Optional[str] = None
    producer: Optional[str] = None
    encryption_status: str
    signature_status: str
    language: Optional[str] = None


class DocumentPageSchema(BaseModel):
    page_number: int
    text: str


class DocumentBlockSchema(BaseModel):
    page_number: int
    block_type: str
    text: Optional[str] = None
    coordinates: Optional[List[float]] = None
    reading_order: int


class DocumentEntitySchema(BaseModel):
    id: UUID
    page_number: int
    entity_type: str
    value: str
    confidence: float
    start_char: int
    end_char: int
    bounding_box: Optional[List[float]] = None
    risk_level: str


class ProcessingLogSchema(BaseModel):
    stage: str
    log_level: str
    message: str
    timestamp: datetime


class ProcessingJobSchema(BaseModel):
    status: str
    progress: int
    error_message: Optional[str] = None
    updated_at: datetime


class DocumentDetailResponse(BaseModel):
    id: UUID
    title: str
    original_filename: str
    storage_path: str
    file_size: int
    mime_type: str
    status: str
    created_at: datetime
    updated_at: datetime
    metadata: Optional[DocumentMetadataSchema] = None
    pages: List[DocumentPageSchema]
    blocks: List[DocumentBlockSchema]
    entities: List[DocumentEntitySchema]
    logs: List[ProcessingLogSchema]
    jobs: List[ProcessingJobSchema]


# ─── Dashboard Stats & Response Schemas ────────────────────────────────
class DashboardStats(BaseModel):
    total_documents: int
    documents_processed: int
    pending_documents: int
    failed_documents: int
    total_users: int


class RecentActivity(BaseModel):
    id: UUID
    title: str
    action: str
    timestamp: datetime

    model_config = {"from_attributes": True}


class ExtendedDashboardStats(BaseModel):
    total_documents: int
    documents_processed: int
    pending_documents: int
    failed_documents: int
    total_users: int
    total_pages: int
    total_entities: int
    risk_distribution: Dict[str, int]
    language_distribution: Dict[str, int]
    entity_distribution: Dict[str, int]


class RecentJobSchema(BaseModel):
    id: UUID
    document_title: str
    job_type: str
    status: str
    progress: int
    error_message: Optional[str] = None
    timestamp: datetime


class DashboardResponse(BaseModel):
    stats: ExtendedDashboardStats
    recent_activity: List[RecentActivity]
    recent_jobs: List[RecentJobSchema]
