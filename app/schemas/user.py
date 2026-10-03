from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, StringConstraints

NombreRequerido = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class UserCreateRequest(BaseModel):
    email: EmailStr
    full_name: NombreRequerido
    apellidos: str | None = None
    telefono: str | None = Field(default=None, max_length=20)
    password: str = Field(..., min_length=1)
    role: str
    branch_id: UUID | None = None


class UserUpdateRequest(BaseModel):
    email: EmailStr
    full_name: NombreRequerido
    apellidos: str | None = None
    telefono: str | None = Field(default=None, max_length=20)
    role: str
    branch_id: UUID | None = None
    password: str | None = None  # None = no cambiar
    is_active: bool | None = None  # None = no cambiar


class UserResponse(BaseModel):
    id: UUID
    full_name: str
    apellidos: str | None = None
    telefono: str | None = None
    email: str
    role: str
    branch_id: UUID | None
    is_active: bool
    ultimo_acceso: datetime | None = None
