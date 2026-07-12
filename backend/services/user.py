"""User service — profile management and password changes."""
import uuid
import logging
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from core.security import hash_password, verify_password
from repositories.user import UserRepository

logger = logging.getLogger("redactai.user")


class UserService:
    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)

    def get_profile(self, user_id: uuid.UUID) -> dict:
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        return {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "avatar_url": user.avatar_url,
            "organization_id": user.organization_id,
            "organization_name": user.organization.name if user.organization else None,
            "roles": [r.name for r in user.roles],
            "is_active": user.is_active,
            "created_at": user.created_at,
            "updated_at": user.updated_at,
        }

    def update_profile(self, user_id: uuid.UUID, full_name: str | None = None, avatar_url: str | None = None) -> dict:
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        update_data = {}
        if full_name is not None:
            update_data["full_name"] = full_name
        if avatar_url is not None:
            update_data["avatar_url"] = avatar_url

        if update_data:
            self.user_repo.update(user, update_data)

        return self.get_profile(user_id)

    def change_password(self, user_id: uuid.UUID, current_password: str, new_password: str) -> None:
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        if not verify_password(current_password, user.hashed_password):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")

        self.user_repo.update(user, {"hashed_password": hash_password(new_password)})
        logger.info(f"Password changed for user {user_id}")
