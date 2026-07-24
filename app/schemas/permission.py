from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints

NombreRolRequerido = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class PermisoResponse(BaseModel):
    id: int
    codigo: str
    nombre: str
    modulo: str
    descripcion: str | None = None


class RolConPermisosResponse(BaseModel):
    id: int
    nombre: str
    descripcion: str | None = None
    activo: bool
    requiere_sucursal: bool
    permisos_editables: bool
    permisos: list[PermisoResponse]


class UpdateRolPermisosRequest(BaseModel):
    permiso_ids: list[int]


class RolCreateRequest(BaseModel):
    nombre: NombreRolRequerido
    descripcion: str | None = None
    permiso_ids: list[int] = Field(default_factory=list)


class RolUpdateRequest(BaseModel):
    nombre: NombreRolRequerido | None = None
    descripcion: str | None = None
    activo: bool | None = None
