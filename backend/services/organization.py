"""Organization service."""
import uuid
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from repositories.organization import OrganizationRepository


class OrganizationService:
    def __init__(self, db: Session):
        self.db = db
        self.org_repo = OrganizationRepository(db)

    def create_organization(self, data: dict) -> dict:
        existing = self.org_repo.get_by_name(data["name"])
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Organization name already exists")

        org = self.org_repo.create({"id": uuid.uuid4(), **data})
        return org

    def get_organizations(self, skip: int = 0, limit: int = 100) -> tuple:
        orgs = self.org_repo.get_all(skip=skip, limit=limit)
        total = self.org_repo.count()
        return orgs, total

    def get_organization(self, org_id: uuid.UUID):
        org = self.org_repo.get_by_id(org_id)
        if not org:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
        return org
