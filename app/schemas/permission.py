from __future__ import annotations

from pydantic import BaseModel


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
    permisos: list[PermisoResponse]


class UpdateRolPermisosRequest(BaseModel):
    permiso_ids: list[int]
