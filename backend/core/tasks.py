import logging
import uuid
from core.celery_app import celery_app
from database.session import SessionLocal
from models.document import Document
from models.document_intelligence import ProcessingJob
from services.ai.orchestrator import AIOrchestrator

logger = logging.getLogger("redactai.tasks")


@celery_app.task(bind=True, name="process_document_pipeline")
def process_document_pipeline(self, document_id: str) -> dict:
    """
    Celery worker task to process documents through the AI Orchestrator.
    """
    try:
        db = SessionLocal()
        try:
            doc = db.query(Document).filter(Document.id == uuid.UUID(document_id)).first()
            if not doc:
                logger.error(f"Document {document_id} not found")
                return {"status": "FAILED", "error": "Document not found"}

            # Create or fetch processing job
            job = db.query(ProcessingJob).filter(
                ProcessingJob.document_id == doc.id,
                ProcessingJob.status.in_(["PENDING", "RUNNING"])
            ).first()

            if not job:
                job = ProcessingJob(
                    id=uuid.uuid4(),
                    document_id=doc.id,
                    job_type="FULL_PIPELINE",
                    status="RUNNING",
                    celery_task_id=getattr(self.request, "id", None) or str(uuid.uuid4()),
                    progress=0,
                )
                db.add(job)
            else:
                job.status = "RUNNING"
                job.celery_task_id = getattr(self.request, "id", None) or str(uuid.uuid4())
            db.commit()

            # Run AI Orchestrator
            try:
                orchestrator = AIOrchestrator(db)
                result = orchestrator.process_document(doc.id, job.id)
            except Exception as orchestrator_exc:
                logger.exception(f"CRITICAL: AIOrchestrator failed for document {document_id}")
                raise orchestrator_exc
            
            logger.info(f"Asynchronous processing complete for document {document_id}")
            return result

        except Exception as exc:
            logger.exception(f"Task failed for document {document_id}: {exc}")
            raise exc
        finally:
            db.close()
    except Exception as top_exc:
        logger.exception(f"Top-level failure in process_document_pipeline for document {document_id}: {top_exc}")
        raise top_exc

