from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, StringConstraints

NombreRequerido = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class BranchCreateRequest(BaseModel):
    nombre: NombreRequerido
    direccion: str | None = None
    telefono: str | None = None
    correo: str | None = None
    administrador_id: UUID | None = None
    administrador_name: str | None = None
    clave: str | None = None


class BranchUpdateRequest(BaseModel):
    nombre: NombreRequerido
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
    creado: datetime | None = None
    creado_por: UUID | None = None
    creador_name: str | None = None
    modificado: datetime | None = None
    modificado_por: UUID | None = None
    modificador_name: str | None = None
