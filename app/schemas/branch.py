from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel


class BranchCreateRequest(BaseModel):
    nombre: str
    direccion: str | None = None
    telefono: str | None = None
    correo: str | None = None
    administrador_id: UUID | None = None
    administrador_name: str | None = None
    clave: str | None = None


class BranchUpdateRequest(BaseModel):
    nombre: str
    direccion: str | None = None
    telefono: str | None = None
    correo: str | None = None
    administrador_id: UUID | None = None
    administrador_name: str | None = None
    clave: str | None = None


class BranchResponse(BaseModel):
    id: UUID
    nombre: str
    direccion: str | None
    telefono: str | None
    correo: str | None
    administrador_id: UUID | None
    administrador_name: str | None
    clave: str | None
    is_active: bool
