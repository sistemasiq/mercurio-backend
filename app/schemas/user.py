from __future__ import annotations

from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, StringConstraints

from app.schemas.auth import RoleEnum

NombreRequerido = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class UserCreateRequest(BaseModel):
    email: EmailStr
    full_name: NombreRequerido
    password: str = Field(..., min_length=1)
    role: RoleEnum
    branch_id: UUID | None = None


class UserUpdateRequest(BaseModel):
    email: EmailStr
    full_name: NombreRequerido
    role: RoleEnum
    branch_id: UUID | None = None
    password: str | None = None  # None = no cambiar


class UserResponse(BaseModel):
    id: UUID
    full_name: str
    email: str
    role: RoleEnum
    branch_id: UUID | None
    is_active: bool
