from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, StringConstraints


class ProveedorBase(BaseModel):
    nombre: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=150)]
    contacto_nombre: str | None = Field(None, max_length=150)
    telefono: str | None = Field(None, max_length=20)
    email: EmailStr | None = None
    notas: str | None = None


class ProveedorCrear(ProveedorBase):
    sucursal_id: UUID


class ProveedorUpdate(BaseModel):
    nombre: str | None = Field(None, max_length=150)
    contacto_nombre: str | None = Field(None, max_length=150)
    telefono: str | None = Field(None, max_length=20)
    email: EmailStr | None = None
    notas: str | None = None
    activo: bool | None = None


class ProveedorOut(ProveedorBase):
    id: UUID
    sucursal_id: UUID
    activo: bool
    creado: datetime | None
    creado_por: UUID | None
    modificado: datetime | None
    modificado_por: UUID | None

    model_config = {"from_attributes": True}
