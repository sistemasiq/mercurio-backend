from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class PaquetesBase(BaseModel):
    sucursal_id: UUID
    nombre: str = Field(..., max_length=150)
    descripcion: str | None = None
    duracion_minutos: int = Field(120, gt=0)
    personas_incluidas: int = Field(10, gt=0)
    precio_base: Decimal = Field(..., ge=0)
    precio_persona_extra: Decimal = Field(Decimal(0), ge=0)


class PaquetesCreate(PaquetesBase):
    pass


class PaquetesUpdate(BaseModel):
    nombre: str | None = Field(None, max_length=150)
    descripcion: str | None = None
    duracion_minutos: int | None = Field(None, gt=0)
    personas_incluidas: int | None = Field(None, gt=0)
    precio_base: Decimal | None = Field(None, ge=0)
    precio_persona_extra: Decimal | None = Field(None, ge=0)
    activo: bool | None = None


class PaquetesOut(PaquetesBase):
    id: UUID
    activo: bool
    creado: datetime
    creado_por: UUID | None
    modificado: datetime | None
    modificado_por: UUID | None

    model_config = {"from_attributes": True}
