"""Document service — handles upload, listing, detail retrieval, deletion, and dashboard stats."""
import uuid
import math
import logging
from typing import Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, UploadFile, status
from repositories.document import DocumentRepository
from repositories.user import UserRepository
from storage.s3 import storage_client, UPLOAD_PREFIX
from models.user import User
from core.config import settings

logger = logging.getLogger("redactai.document")

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "image/png",
    "image/jpeg",
    "image/jpg",
    "image/tiff",
}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


class DocumentService:
    def __init__(self, db: Session):
        self.db = db
        self.doc_repo = DocumentRepository(db)
        self.user_repo = UserRepository(db)

    async def upload_document(self, file: UploadFile, title: str, user: User, background_tasks = None) -> dict:
        import hashlib
        import os
        from models.document import Document
        from models.ai_models import AuditLog, SecurityAlert

        # 1. Validate mime type
        if file.content_type not in ALLOWED_MIME_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File type '{file.content_type}' not supported. Allowed: PDF, DOCX, PNG, JPEG, TIFF",
            )

        # Read and validate file size
        content = await file.read()
        file_size = len(content)
        if file_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File exceeds maximum size of {MAX_FILE_SIZE // (1024*1024)} MB",
            )

        # 2. Filename sanitization
        original_name = file.filename or "unnamed"
        sanitized_filename = os.path.basename(original_name).replace("..", "").strip()

        # 3. Validate magic bytes / file signature
        signature_map = {
            "application/pdf": b"%PDF",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": b"PK\x03\x04",
            "image/png": b"\x89PNG\r\n\x1a\n",
            "image/jpeg": b"\xff\xd8\xff",
            "image/jpg": b"\xff\xd8\xff",
            "image/tiff": (b"II*\x00", b"MM\x00*")
        }
        
        sig = signature_map.get(file.content_type)
        if sig:
            matched = False
            if isinstance(sig, tuple):
                matched = any(content.startswith(s) for s in sig)
            else:
                matched = content.startswith(sig)
            if not matched:
                alert = SecurityAlert(
                    event_type="SUSPICIOUS_UPLOAD_SIGNATURE_MISMATCH",
                    severity="CRITICAL",
                    description=f"File upload blocked: content-type {file.content_type} signature mismatch.",
                    details={"filename": sanitized_filename}
                )
                self.db.add(alert)
                self.db.commit()
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File contents do not match specified MIME type signature.")

        # 4. SHA-256 integrity hash duplicate checks
        file_sha256 = hashlib.sha256(content).hexdigest()
        duplicate = self.db.query(Document).filter(Document.sha256 == file_sha256).first()
        if duplicate:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Duplicate file upload detected. File has already been uploaded.")

        # 5. Mock virus / malware scanning
        if b"EICAR-STANDARD" in content or b"malware-trigger" in content:
            alert = SecurityAlert(
                event_type="MALICIOUS_UPLOAD_BLOCKED",
                severity="CRITICAL",
                description=f"Malware scanning blocked malicious upload: {sanitized_filename}",
                details={"sha256": file_sha256}
            )
            self.db.add(alert)
            self.db.commit()
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File rejected: potential malware detected during safety scan.")

        if not user.organization_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User must belong to an organization to upload documents",
            )

        doc_id = uuid.uuid4()

        # Upload to MinIO
        storage_path = storage_client.upload_file(
            file_content=content,
            document_id=str(doc_id),
            filename=sanitized_filename,
            content_type=file.content_type,
            prefix=UPLOAD_PREFIX,
        )

        # Create database record
        try:
            logger.info("BEFORE STEP 7: Database record creation started")
            document_data = {
                "id": doc_id,
                "title": title,
                "original_filename": sanitized_filename,
                "storage_path": storage_path,
                "file_size": file_size,
                "mime_type": file.content_type,
                "sha256": file_sha256,
                "owner_id": user.id,
                "organization_id": user.organization_id,
                "status": "Pending",
            }
            logger.info("AFTER STEP 7: Database record creation started")

            logger.info("BEFORE STEP 8: Database record creation completed")
            document = self.doc_repo.create(document_data)
            logger.info(f"AFTER STEP 8: Database record creation completed for document ID: {doc_id}")
        except Exception as e:
            logger.exception("Exception in Step 7 or 8: Database record creation")
            raise e


        # Save audit log for document upload
        try:
            audit = AuditLog(
                user_id=user.id,
                user_email=user.email,
                action="UPLOAD",
                resource=f"Document_{doc_id}",
                result="SUCCESS"
            )
            self.db.add(audit)
            self.db.commit()
        except Exception as e:
            logger.error(f"Failed to save audit log: {e}\n{traceback.format_exc()}")
            raise e


        # Create initial processing job
        from models.document_intelligence import ProcessingJob
        job = ProcessingJob(
            id=uuid.uuid4(),
            document_id=doc_id,
            job_type="FULL_PIPELINE",
            status="PENDING",
            progress=0
        )
        self.db.add(job)
        self.db.commit()

        # Trigger async processing pipeline (CTO requirement: always Celery)
        try:
            from core.tasks import process_document_pipeline
            # If in single/huggingface mode or background_tasks is supplied, run synchronously/locally
            if settings.DEPLOYMENT_MODE in ("single", "huggingface") or background_tasks:
                def run_sync_wrapper(doc_id_str: str):
                    import traceback
                    try:
                        logger.info(f"Background task execution started for document {doc_id_str}")
                        process_document_pipeline(doc_id_str)
                        logger.info(f"Background task execution completed successfully for document {doc_id_str}")
                    except Exception as e:
                        logger.error(
                            f"CRITICAL: Background task failed for document {doc_id_str}. "
                            f"Preventing propagation to prevent ASGI crash. Error: {e}\n{traceback.format_exc()}"
                        )
                    
                if background_tasks:
                    background_tasks.add_task(run_sync_wrapper, str(doc_id))
                    logger.info(f"Processing pipeline dispatched via BackgroundTasks for document {doc_id}")
                else:
                    run_sync_wrapper(str(doc_id))
                    logger.info(f"Processing pipeline executed synchronously for document {doc_id}")
            else:

                process_document_pipeline.delay(str(doc_id))
                logger.info(f"Processing pipeline triggered asynchronously via Celery for document {doc_id}")
        except Exception as e:
            logger.error(f"Failed to queue processing task for document {doc_id}: {e}")
            job.status = "FAILED"
            job.error_message = f"Task dispatch failed: {str(e)}"
            document.status = "Failed"
            self.db.commit()

        return document

    def get_documents(
        self,
        user: User,
        search: Optional[str] = None,
        status_filter: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        skip = (page - 1) * page_size
        documents, total = self.doc_repo.get_documents_paginated(
            organization_id=user.organization_id,
            search=search,
            status=status_filter,
            sort_by=sort_by,
            sort_order=sort_order,
            skip=skip,
            limit=page_size,
        )
        total_pages = math.ceil(total / page_size) if total > 0 else 1

        return {
            "documents": documents,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        }

    def get_document(self, document_id: uuid.UUID, user: User) -> dict:
        doc = self.doc_repo.get_by_id(document_id)
        if not doc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
        if doc.organization_id != user.organization_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        
        # Fetch metadata, pages, blocks, entities, logs
        from models.document_intelligence import DocumentMetadata, DocumentPage, DocumentBlock, DocumentEntity, ProcessingJob
        from models.ai_models import ProcessingLog
        
        metadata = self.db.query(DocumentMetadata).filter(DocumentMetadata.document_id == doc.id).first()
        pages = self.db.query(DocumentPage).filter(DocumentPage.document_id == doc.id).order_by(DocumentPage.page_number.asc()).all()
        blocks = self.db.query(DocumentBlock).filter(DocumentBlock.document_id == doc.id).order_by(DocumentBlock.page_number.asc(), DocumentBlock.reading_order.asc()).all()
        entities = self.db.query(DocumentEntity).filter(DocumentEntity.document_id == doc.id).order_by(DocumentEntity.page_number.asc(), DocumentEntity.start_char.asc()).all()
        logs = self.db.query(ProcessingLog).filter(ProcessingLog.document_id == doc.id).order_by(ProcessingLog.created_at.asc()).all()
        jobs = self.db.query(ProcessingJob).filter(ProcessingJob.document_id == doc.id).order_by(ProcessingJob.created_at.desc()).all()

        return {
            "id": doc.id,
            "title": doc.title,
            "original_filename": doc.original_filename,
            "storage_path": doc.storage_path,
            "file_size": doc.file_size,
            "mime_type": doc.mime_type,
            "status": doc.status,
            "created_at": doc.created_at,
            "updated_at": doc.updated_at,
            "metadata": {
                "file_size": metadata.file_size,
                "mime_type": metadata.mime_type,
                "file_type": metadata.file_type,
                "page_count": metadata.page_count,
                "author": metadata.author,
                "producer": metadata.producer,
                "encryption_status": metadata.encryption_status,
                "signature_status": metadata.signature_status,
                "language": metadata.language,
            } if metadata else None,
            "pages": [{"page_number": p.page_number, "text": p.text} for p in pages],
            "blocks": [
                {
                    "page_number": b.page_number,
                    "block_type": b.block_type,
                    "text": b.text,
                    "coordinates": b.coordinates,
                    "reading_order": b.reading_order
                } for b in blocks
            ],
            "entities": [
                {
                    "id": e.id,
                    "page_number": e.page_number,
                    "entity_type": e.entity_type,
                    "value": e.value,
                    "confidence": e.confidence,
                    "start_char": e.start_char,
                    "end_char": e.end_char,
                    "bounding_box": e.bounding_box,
                    "risk_level": e.risk_level
                } for e in entities
            ],
            "logs": [
                {
                    "stage": l.stage,
                    "log_level": l.log_level,
                    "message": l.message,
                    "timestamp": l.created_at
                } for l in logs
            ],
            "jobs": [
                {
                    "status": j.status,
                    "progress": j.progress,
                    "error_message": j.error_message,
                    "updated_at": j.updated_at
                } for j in jobs
            ]
        }

    def delete_document(self, document_id: uuid.UUID, user: User) -> None:
        doc = self.doc_repo.get_by_id(document_id)
        if not doc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
        if doc.organization_id != user.organization_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

        # Delete from MinIO
        storage_client.delete_file(doc.storage_path)

        # Delete from database
        self.doc_repo.delete(document_id)
        logger.info(f"Document {document_id} deleted by user {user.id}")

    def get_dashboard_stats(self, user: User) -> dict:
        doc_counts = self.doc_repo.count_by_status(organization_id=user.organization_id)
        user_count = len(self.user_repo.get_users_by_organization(user.organization_id)) if user.organization_id else 0

        # Query metadata tables to extract advanced stats
        from models.document import Document
        from models.document_intelligence import DocumentMetadata, DocumentEntity, ProcessingJob
        from sqlalchemy import func
        
        # Total Pages Processed
        total_pages = self.db.query(func.sum(DocumentMetadata.page_count)).\
            join(Document, Document.id == DocumentMetadata.document_id).\
            filter(Document.organization_id == user.organization_id).scalar() or 0

        # Total Entities Detected
        total_entities = self.db.query(func.count(DocumentEntity.id)).\
            join(Document, Document.id == DocumentEntity.document_id).\
            filter(Document.organization_id == user.organization_id).scalar() or 0

        # Risk Distribution
        risk_dist = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        risk_query = self.db.query(DocumentEntity.risk_level, func.count(DocumentEntity.id)).\
            join(Document, Document.id == DocumentEntity.document_id).\
            filter(Document.organization_id == user.organization_id).\
            group_by(DocumentEntity.risk_level).all()
        for r_lvl, count in risk_query:
            if r_lvl in risk_dist:
                risk_dist[r_lvl] = count

        # Language Distribution
        lang_dist = {}
        lang_query = self.db.query(DocumentMetadata.language, func.count(DocumentMetadata.id)).\
            join(Document, Document.id == DocumentMetadata.document_id).\
            filter(Document.organization_id == user.organization_id).\
            group_by(DocumentMetadata.language).all()
        for lang, count in lang_query:
            if lang:
                lang_dist[lang] = count

        # Entity Distribution
        entity_dist = {}
        ent_query = self.db.query(DocumentEntity.entity_type, func.count(DocumentEntity.id)).\
            join(Document, Document.id == DocumentEntity.document_id).\
            filter(Document.organization_id == user.organization_id).\
            group_by(DocumentEntity.entity_type).all()
        for ent_type, count in ent_query:
            entity_dist[ent_type] = count

        # Recent AI Jobs
        recent_jobs_query = self.db.query(ProcessingJob, Document.title).\
            join(Document, Document.id == ProcessingJob.document_id).\
            filter(Document.organization_id == user.organization_id).\
            order_by(ProcessingJob.created_at.desc()).limit(10).all()
        
        recent_jobs = [
            {
                "id": job.id,
                "document_title": doc_title,
                "job_type": job.job_type,
                "status": job.status,
                "progress": job.progress,
                "error_message": job.error_message,
                "timestamp": job.created_at
            }
            for job, doc_title in recent_jobs_query
        ]

        return {
            "total_documents": doc_counts["total"],
            "documents_processed": doc_counts["processed"],
            "pending_documents": doc_counts["pending"],
            "failed_documents": doc_counts["failed"],
            "total_users": user_count,
            "total_pages": total_pages,
            "total_entities": total_entities,
            "risk_distribution": risk_dist,
            "language_distribution": lang_dist,
            "entity_distribution": entity_dist,
            "recent_jobs": recent_jobs
        }

    def get_recent_activity(self, user: User, limit: int = 10) -> list:
        documents, _ = self.doc_repo.get_documents_paginated(
            organization_id=user.organization_id,
            sort_by="created_at",
            sort_order="desc",
            skip=0,
            limit=limit,
        )
        return [
            {
                "id": doc.id,
                "title": doc.title,
                "action": f"Document '{doc.original_filename}' — {doc.status}",
                "timestamp": doc.created_at,
            }
            for doc in documents
        ]

