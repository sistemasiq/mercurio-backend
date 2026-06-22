from uuid import UUID
from datetime import datetime

from pydantic import BaseModel, Field


class TiposEventoBase(BaseModel):
    nombre: str = Field(..., max_length=100)
    descripcion: str | None = None


class TiposEventoCreate(TiposEventoBase): pass


class TiposEventoUpdate(BaseModel):
    nombre: str | None = Field(None, max_length=100)
    descripcion: str | None = None
    activo: bool | None = None


class TiposEventoOut(TiposEventoBase):
    id: UUID
    activo: bool
    creado: datetime
    creado_por: UUID | None
    modificado: datetime | None
    modificado_por: UUID | None

    model_config = {'from_attributes': True}
