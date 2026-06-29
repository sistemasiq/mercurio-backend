from uuid import UUID
from datetime import datetime

from pydantic import BaseModel, Field


class MetodosPagoBase(BaseModel):
    nombre: str = Field(..., max_length=100)
    descripcion: str | None = None


class MetodosPagoCreate(MetodosPagoBase): pass


class MetodosPagoUpdate(BaseModel):
    nombre: str | None = Field(None, max_length=100)
    descripcion: str | None = None
    activo: bool | None = None


class MetodosPagoOut(MetodosPagoBase):
    id: UUID
    activo: bool
    creado: datetime
    creado_por: UUID | None
    modificado: datetime | None
    modificado_por: UUID | None

    model_config = {'from_attributes': True}
