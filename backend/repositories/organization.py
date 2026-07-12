"""Organization repository."""
from typing import Optional
from sqlalchemy.orm import Session
from repositories.base import BaseRepository
from models.organization import Organization


class OrganizationRepository(BaseRepository[Organization]):
    def __init__(self, db: Session):
        super().__init__(Organization, db)

    def get_by_name(self, name: str) -> Optional[Organization]:
        return self.db.query(Organization).filter(Organization.name == name).first()
