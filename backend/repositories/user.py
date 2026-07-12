"""User repository with authentication-specific queries."""
import uuid
from typing import Optional, List
from sqlalchemy.orm import Session
from repositories.base import BaseRepository
from models.user import User, RefreshToken
from models.role import Role, user_roles


class UserRepository(BaseRepository[User]):
    def __init__(self, db: Session):
        super().__init__(User, db)

    def get_by_email(self, email: str) -> Optional[User]:
        return self.db.query(User).filter(User.email == email).first()

    def get_user_roles(self, user_id: uuid.UUID) -> List[Role]:
        user = self.get_by_id(user_id)
        return user.roles if user else []

    def assign_role(self, user_id: uuid.UUID, role_id: uuid.UUID) -> None:
        self.db.execute(user_roles.insert().values(user_id=user_id, role_id=role_id))
        self.db.commit()

    def get_users_by_organization(self, org_id: uuid.UUID, skip: int = 0, limit: int = 100) -> List[User]:
        return (
            self.db.query(User)
            .filter(User.organization_id == org_id)
            .offset(skip)
            .limit(limit)
            .all()
        )


class RefreshTokenRepository(BaseRepository[RefreshToken]):
    def __init__(self, db: Session):
        super().__init__(RefreshToken, db)

    def get_by_token(self, token: str) -> Optional[RefreshToken]:
        return self.db.query(RefreshToken).filter(
            RefreshToken.token == token,
            RefreshToken.is_revoked == False,
        ).first()

    def revoke_all_for_user(self, user_id: uuid.UUID) -> None:
        self.db.query(RefreshToken).filter(
            RefreshToken.user_id == user_id,
            RefreshToken.is_revoked == False,
        ).update({"is_revoked": True})
        self.db.commit()

    def revoke_token(self, token: str) -> None:
        refresh_token = self.get_by_token(token)
        if refresh_token:
            refresh_token.is_revoked = True
            self.db.commit()
