from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel


class BranchCreateRequest(BaseModel):
    nombre: str
    direccion: str | None = None
    telefono: str | None = None


class BranchResponse(BaseModel):
    id: UUID
    nombre: str
    direccion: str | None
    telefono: str | None
    is_active: bool
