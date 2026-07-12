"""Pydantic schemas for user profile operations."""
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field


class UserProfile(BaseModel):
    id: UUID
    email: EmailStr
    full_name: str
    avatar_url: str | None = None
    organization_id: UUID | None = None
    organization_name: str | None = None
    roles: list[str] = []
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UpdateProfileRequest(BaseModel):
    full_name: str | None = Field(None, min_length=2, max_length=255)
    avatar_url: str | None = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=128)
