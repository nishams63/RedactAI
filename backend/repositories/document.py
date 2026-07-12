"""Document repository with search, filter, and pagination."""
import uuid
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import or_
from repositories.base import BaseRepository
from models.document import Document
from models.document_intelligence import ProcessingJob


class DocumentRepository(BaseRepository[Document]):
    def __init__(self, db: Session):
        super().__init__(Document, db)

    def get_documents_paginated(
        self,
        organization_id: Optional[uuid.UUID] = None,
        owner_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        skip: int = 0,
        limit: int = 20,
    ) -> Tuple[List[Document], int]:
        """Return paginated, filtered, and searchable documents list."""
        query = self.db.query(Document)

        if organization_id:
            query = query.filter(Document.organization_id == organization_id)
        if owner_id:
            query = query.filter(Document.owner_id == owner_id)
        if status:
            query = query.filter(Document.status == status)
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    Document.title.ilike(search_term),
                    Document.original_filename.ilike(search_term),
                )
            )

        total = query.count()

        # Sorting
        sort_column = getattr(Document, sort_by, Document.created_at)
        if sort_order == "asc":
            query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(sort_column.desc())

        documents = query.offset(skip).limit(limit).all()
        return documents, total

    def get_by_organization(self, org_id: uuid.UUID) -> List[Document]:
        return self.db.query(Document).filter(Document.organization_id == org_id).all()

    def count_by_status(self, organization_id: Optional[uuid.UUID] = None) -> dict:
        """Return counts per status for dashboard widgets."""
        query = self.db.query(Document)
        if organization_id:
            query = query.filter(Document.organization_id == organization_id)

        total = query.count()
        processed = query.filter(Document.status == "Processed").count()
        pending = query.filter(Document.status == "Pending").count()
        failed = query.filter(Document.status == "Failed").count()

        return {
            "total": total,
            "processed": processed,
            "pending": pending,
            "failed": failed,
        }


class ProcessingJobRepository(BaseRepository[ProcessingJob]):
    def __init__(self, db: Session):
        super().__init__(ProcessingJob, db)

    def get_jobs_for_document(self, document_id: uuid.UUID) -> List[ProcessingJob]:
        return (
            self.db.query(ProcessingJob)
            .filter(ProcessingJob.document_id == document_id)
            .order_by(ProcessingJob.created_at.desc())
            .all()
        )
