"""Pydantic schemas for organization operations."""
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field


class OrganizationCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    logo_url: str | None = None
    address: str | None = None
    email: EmailStr | None = None
    phone: str | None = Field(None, max_length=50)


class OrganizationResponse(BaseModel):
    id: UUID
    name: str
    logo_url: str | None = None
    address: str | None = None
    email: str | None = None
    phone: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class OrganizationListResponse(BaseModel):
    organizations: list[OrganizationResponse]
    total: int
