"""Document API endpoints — upload, list, detail, delete, and dashboard."""
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, UploadFile, File, Form, Query
from sqlalchemy.orm import Session
from dependencies import get_db, get_current_user, check_permissions
from schemas.document import (
    DocumentResponse, DocumentListResponse, DocumentUploadResponse,
    DashboardResponse, DashboardStats, RecentActivity, DocumentDetailResponse
)
from schemas.auth import MessageResponse
from services.document import DocumentService
from models.user import User

router = APIRouter(prefix="/documents", tags=["Documents"])


from fastapi import BackgroundTasks

@router.post("/upload", response_model=DocumentUploadResponse, status_code=201)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: str = Form(...),
    current_user: User = Depends(check_permissions(["Admin"])),
    db: Session = Depends(get_db),
):
    """Upload a new document (PDF, DOCX, or Image). Triggers async processing pipeline."""
    service = DocumentService(db)
    document = await service.upload_document(file=file, title=title, user=current_user, background_tasks=background_tasks)
    return {
        "document": document,
        "message": "Document uploaded successfully. Processing pipeline started.",
    }


@router.get("", response_model=DocumentListResponse)
def list_documents(
    search: Optional[str] = Query(None, description="Search by document title or filename"),
    status: Optional[str] = Query(None, description="Filter by status (Pending, Processed, Failed)"),
    sort_by: str = Query("created_at", description="Field to sort by"),
    sort_order: str = Query("desc", description="Sort order (asc or desc)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List documents with search, pagination, sorting, and filtering."""
    service = DocumentService(db)
    return service.get_documents(
        user=current_user,
        search=search,
        status_filter=status,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
    )


@router.get("/dashboard", response_model=DashboardResponse)
def get_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get dashboard statistics and recent activity."""
    service = DocumentService(db)
    stats = service.get_dashboard_stats(user=current_user)
    activity = service.get_recent_activity(user=current_user)
    return {
        "stats": stats,
        "recent_activity": activity,
        "recent_jobs": stats["recent_jobs"]
    }


@router.get("/{document_id}", response_model=DocumentDetailResponse)
def get_document(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get document details by ID."""
    service = DocumentService(db)
    return service.get_document(document_id=document_id, user=current_user)


@router.delete("/{document_id}", response_model=MessageResponse)
def delete_document(
    document_id: uuid.UUID,
    current_user: User = Depends(check_permissions(["Admin", "Legal Officer"])),
    db: Session = Depends(get_db),
):
    """Delete a document (Admin or Legal Officer only)."""
    from models.ai_models import AuditLog
    
    service = DocumentService(db)
    service.delete_document(document_id=document_id, user=current_user)
    
    audit = AuditLog(
        user_id=current_user.id,
        user_email=current_user.email,
        action="DELETE",
        resource=f"Document_{document_id}",
        result="SUCCESS"
    )
    db.add(audit)
    db.commit()
    
    return {"message": "Document deleted successfully"}


@router.get("/local-preview/{prefix}/{document_id}/{filename}", tags=["Documents"])
def preview_local_file(
    prefix: str, 
    document_id: str, 
    filename: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Serve locally stored files, verifying active organization access and writing audit log."""
    from models.document import Document
    from models.ai_models import AuditLog, SecurityAlert
    
    try:
        doc_uuid = uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid document ID format")
        
    doc = db.query(Document).filter(Document.id == doc_uuid).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    user_roles = [r.name for r in current_user.roles]
    if "Admin" not in user_roles and doc.organization_id != current_user.organization_id:
        alert = SecurityAlert(
            event_type="UNAUTHORIZED_ACCESS_ATTEMPT",
            severity="HIGH",
            description=f"User {current_user.email} attempted to preview document {document_id} of org {doc.organization_id} (User org: {current_user.organization_id}).",
            details={"user_id": str(current_user.id), "document_id": document_id}
        )
        db.add(alert)
        db.commit()
        raise HTTPException(status_code=403, detail="Access denied to this document's resources")

    audit = AuditLog(
        user_id=current_user.id,
        user_email=current_user.email,
        action="DOWNLOAD",
        resource=f"Document_{document_id}",
        result="SUCCESS"
    )
    db.add(audit)
    db.commit()

    import os
    from fastapi.responses import FileResponse
    local_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "local_storage",
        prefix,
        document_id,
        filename
    )
    if not os.path.exists(local_path):
        raise HTTPException(status_code=404, detail="Local file not found")
    return FileResponse(local_path)
