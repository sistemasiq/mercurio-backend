from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class SucursalBase(BaseModel):
    nombre: str = Field(..., max_length=150)
    direccion: str | None = None
    telefono: str | None = Field(None, max_length=10, pattern=r"^\d{10}$")


class SucursalCreate(SucursalBase):
    pass


class SucursalUpdate(BaseModel):
    nombre: str | None = Field(None, max_length=150)
    direccion: str | None = None
    telefono: str | None = Field(None, max_length=10, pattern=r"^\d{10}$")
    activo: bool | None = None


class SucursalOut(SucursalBase):
    id: UUID
    telefono: str | None = None  # sin patrón — datos existentes en DB pueden no cumplirlo
    activo: bool
    creado: datetime
    creado_por: UUID | None
    modificado: datetime | None
    modificado_por: UUID | None

    model_config = {"from_attributes": True}
