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
        import sys
        import traceback
        from models.document import Document
        from models.ai_models import AuditLog, SecurityAlert

        def log_stage_exception(stage_name: str, e: Exception):
            exc_type, exc_value, exc_tb = sys.exc_info()
            tb_list = traceback.extract_tb(exc_tb)
            line_num = "unknown"
            filename = "unknown"
            func_name = "unknown"
            if tb_list:
                last_tb = tb_list[-1]
                line_num = last_tb.lineno
                filename = last_tb.filename
                func_name = last_tb.name
            logger.exception(
                f"[STAGE ERROR] Failed at stage: {stage_name}. "
                f"Exception: {type(e).__name__}: {e}. "
                f"Line number: {line_num} in {filename} ({func_name})"
            )

        # Stage 1: Validate MIME type
        try:
            logger.info("BEFORE STAGE 1: Mime type validation")
            if file.content_type not in ALLOWED_MIME_TYPES:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"File type '{file.content_type}' not supported. Allowed: PDF, DOCX, PNG, JPEG, TIFF",
                )
            logger.info("AFTER STAGE 1: Mime type validation succeeded")
        except Exception as e:
            log_stage_exception("Mime type validation", e)
            raise

        # Stage 2: Read file & validate size
        try:
            logger.info("BEFORE STAGE 2: Read file & size check")
            content = await file.read()
            file_size = len(content)
            if file_size > MAX_FILE_SIZE:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"File exceeds maximum size of {MAX_FILE_SIZE // (1024*1024)} MB",
                )
            logger.info(f"AFTER STAGE 2: Read file & size check. Size: {file_size} bytes")
        except Exception as e:
            log_stage_exception("Read file & size check", e)
            raise

        # Stage 3: Filename sanitization
        try:
            logger.info("BEFORE STAGE 3: Filename sanitization")
            original_name = file.filename or "unnamed"
            sanitized_filename = os.path.basename(original_name).replace("..", "").strip()
            logger.info(f"AFTER STAGE 3: Filename sanitized: {sanitized_filename}")
        except Exception as e:
            log_stage_exception("Filename sanitization", e)
            raise

        # Stage 4: Validate magic bytes / file signature
        try:
            logger.info("BEFORE STAGE 4: Magic bytes validation")
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
            logger.info("AFTER STAGE 4: Magic bytes validation passed")
        except Exception as e:
            log_stage_exception("Magic bytes validation", e)
            raise

        # Stage 5: Integrity duplicate check
        try:
            logger.info("BEFORE STAGE 5: Duplicate checksum check")
            file_sha256 = hashlib.sha256(content).hexdigest()
            duplicate = self.db.query(Document).filter(Document.sha256 == file_sha256).first()
            if duplicate:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Duplicate file upload detected. File has already been uploaded.")
            logger.info("AFTER STAGE 5: Duplicate checksum check passed")
        except Exception as e:
            log_stage_exception("Duplicate checksum check", e)
            raise

        # Stage 6: Malware scanning
        try:
            logger.info("BEFORE STAGE 6: Malware scanner check")
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
            logger.info("AFTER STAGE 6: Malware scanner check passed")
        except Exception as e:
            log_stage_exception("Malware scanner check", e)
            raise

        # Stage 7: Org check
        try:
            logger.info("BEFORE STAGE 7: Organization verification")
            if not user.organization_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User must belong to an organization to upload documents",
                )
            logger.info(f"AFTER STAGE 7: Organization verification: {user.organization_id}")
        except Exception as e:
            log_stage_exception("Organization verification", e)
            raise

        # Stage 8: Storage upload
        try:
            logger.info("BEFORE STAGE 8: Uploading file to storage provider")
            doc_id = uuid.uuid4()
            storage_path = storage_client.upload_file(
                file_content=content,
                document_id=str(doc_id),
                filename=sanitized_filename,
                content_type=file.content_type,
                prefix=UPLOAD_PREFIX,
            )
            logger.info(f"AFTER STAGE 8: Uploaded to storage. Path: {storage_path}")
        except Exception as e:
            log_stage_exception("Storage upload", e)
            raise

        # Stage 9: Database record insert
        try:
            logger.info("BEFORE STAGE 9: Database record insert started")
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
            document = self.doc_repo.create(document_data)
            logger.info(f"AFTER STAGE 9: Database record insert completed. Doc ID: {doc_id}")
        except Exception as e:
            log_stage_exception("Database record insert", e)
            raise

        # Stage 10: Audit logging
        try:
            logger.info("BEFORE STAGE 10: Audit logging insert")
            audit = AuditLog(
                user_id=user.id,
                user_email=user.email,
                action="UPLOAD",
                resource=f"Document_{doc_id}",
                result="SUCCESS"
            )
            self.db.add(audit)
            self.db.commit()
            logger.info("AFTER STAGE 10: Audit logging insert succeeded")
        except Exception as e:
            log_stage_exception("Audit logging insert", e)
            raise

        # Stage 11: Processing job model insert
        try:
            logger.info("BEFORE STAGE 11: ProcessingJob database insert")
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
            logger.info(f"AFTER STAGE 11: ProcessingJob database insert succeeded. Job ID: {job.id}")
        except Exception as e:
            log_stage_exception("ProcessingJob database insert", e)
            raise

        # Stage 12: Trigger processing pipeline
        try:
            logger.info("BEFORE STAGE 12: Trigger async processing pipeline")
            from core.tasks import process_document_pipeline
            if settings.DEPLOYMENT_MODE == "celery":
                logger.info("Celery task dispatch triggered")
                process_document_pipeline.delay(str(doc_id))
                logger.info(f"AFTER STAGE 12: Celery task delay dispatched for doc {doc_id}")
            else:
                logger.info("Running task synchronously")
                process_document_pipeline(str(doc_id))
                logger.info(f"AFTER STAGE 12: Executed task synchronously for doc {doc_id}")
                try:
                    self.db.refresh(document)
                except Exception:
                    pass
        except Exception as e:
            log_stage_exception("Trigger async processing pipeline", e)
            logger.error(f"Failed to queue processing task for document {doc_id}: {e}")
            job.status = "FAILED"
            job.error_message = f"Task dispatch failed: {str(e)}"
            document.status = "Failed"
            self.db.commit()
            raise



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
        import os
        import shutil
        from storage.s3 import _LOCAL_STORAGE_DIR
        from models.document import Document, DocumentVersion
        from models.document_intelligence import DocumentMetadata, DocumentPage, DocumentBlock, DocumentEntity, ProcessingJob
        from models.ai_models import DetectedEntity, Redaction, ComplianceResult, ProcessingLog, HumanReview
        from models.ml_models import MLPrediction

        doc = self.doc_repo.get_by_id(document_id)
        if not doc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
        if doc.organization_id != user.organization_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

        # 1. Clean up file resources (original, redacted, and OCR files)
        storage_path_str = doc.storage_path or ""
        try:
            storage_client.delete_file(storage_path_str)
        except Exception as e:
            logger.warning(f"Failed to delete original file {storage_path_str}: {e}")

        # Delete redacted and ocr files if they exist
        try:
            if storage_path_str.startswith("local://"):
                storage_client.delete_file(storage_path_str.replace("uploads/", "redacted/"))
                storage_client.delete_file(f"local://ocr/{doc.id}/{doc.id}_ocr.json")

                # Clean up document folders on the filesystem
                for prefix in ["uploads", "redacted", "ocr"]:
                    dir_to_remove = os.path.join(_LOCAL_STORAGE_DIR, prefix, str(doc.id))
                    if os.path.exists(dir_to_remove):
                        try:
                            shutil.rmtree(dir_to_remove)
                            logger.info(f"Deleted local directory: {dir_to_remove}")
                        except Exception as e:
                            logger.error(f"Failed to remove directory {dir_to_remove}: {e}")
            else:
                storage_client.delete_file(storage_path_str.replace("uploads/", "redacted/"))
                storage_client.delete_file(f"ocr/{doc.id}/{doc.id}_ocr.json")
        except Exception as e:
            logger.warning(f"Non-fatal error cleaning up storage files for doc {document_id}: {e}")

        # 2. Delete related child records — order matters for FK constraints
        #    Redaction → DetectedEntity (Redaction.detected_entity_id FK)
        try:
            self.db.query(Redaction).filter(Redaction.document_id == document_id).delete(synchronize_session=False)
            self.db.query(DetectedEntity).filter(DetectedEntity.document_id == document_id).delete(synchronize_session=False)
            self.db.query(ComplianceResult).filter(ComplianceResult.document_id == document_id).delete(synchronize_session=False)
            self.db.query(ProcessingLog).filter(ProcessingLog.document_id == document_id).delete(synchronize_session=False)
            self.db.query(HumanReview).filter(HumanReview.document_id == document_id).delete(synchronize_session=False)
            self.db.query(MLPrediction).filter(MLPrediction.document_id == document_id).delete(synchronize_session=False)
            self.db.query(DocumentMetadata).filter(DocumentMetadata.document_id == document_id).delete(synchronize_session=False)
            self.db.query(DocumentPage).filter(DocumentPage.document_id == document_id).delete(synchronize_session=False)
            self.db.query(DocumentBlock).filter(DocumentBlock.document_id == document_id).delete(synchronize_session=False)
            self.db.query(DocumentEntity).filter(DocumentEntity.document_id == document_id).delete(synchronize_session=False)
            self.db.query(ProcessingJob).filter(ProcessingJob.document_id == document_id).delete(synchronize_session=False)
            self.db.query(DocumentVersion).filter(DocumentVersion.document_id == document_id).delete(synchronize_session=False)
            self.db.flush()
        except Exception as e:
            logger.error(f"Error deleting child records for document {document_id}: {e}")
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete document related records: {str(e)}",
            )

        # 3. Delete the parent Document record
        try:
            self.db.query(Document).filter(Document.id == document_id).delete(synchronize_session=False)
            self.db.commit()
        except Exception as e:
            logger.error(f"Error deleting parent Document {document_id}: {e}")
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete document: {str(e)}",
            )
        logger.info(f"Document {document_id} and all associated files/records deleted by user {user.id}")

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

