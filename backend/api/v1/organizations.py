"""Organization API endpoints."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from dependencies import get_db, get_current_user, check_permissions
from schemas.organization import OrganizationCreate, OrganizationResponse, OrganizationListResponse
from services.organization import OrganizationService
from models.user import User

router = APIRouter(prefix="/organizations", tags=["Organizations"])


@router.get("", response_model=OrganizationListResponse)
def list_organizations(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all organizations."""
    service = OrganizationService(db)
    orgs, total = service.get_organizations(skip=skip, limit=limit)
    return {"organizations": orgs, "total": total}


@router.post("", response_model=OrganizationResponse, status_code=201)
def create_organization(
    request: OrganizationCreate,
    current_user: User = Depends(check_permissions(["Admin"])),
    db: Session = Depends(get_db),
):
    """Create a new organization (Admin only)."""
    service = OrganizationService(db)
    return service.create_organization(request.model_dump())
