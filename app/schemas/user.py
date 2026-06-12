from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, EmailStr

from app.schemas.auth import RoleEnum


class UserCreateRequest(BaseModel):
    email: EmailStr
    full_name: str
    password: str
    role: RoleEnum
    branch_id: UUID | None = None


class UserResponse(BaseModel):
    id: UUID
    full_name: str
    email: str
    role: RoleEnum
    branch_id: UUID | None
    is_active: bool
