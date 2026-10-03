from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class PresentacionCrear(BaseModel):
    nombre: str = Field(..., max_length=100)
    equivalencia_base: Decimal = Field(..., gt=0)


class PresentacionUpdate(BaseModel):
    nombre: str | None = Field(None, max_length=100)
    equivalencia_base: Decimal | None = Field(None, gt=0)
    activo: bool | None = None


class PresentacionOut(BaseModel):
    id: UUID
    insumo_id: UUID
    nombre: str
    equivalencia_base: Decimal
    activo: bool
    creado: datetime | None
    creado_por: UUID | None
    modificado: datetime | None
    modificado_por: UUID | None

    model_config = {"from_attributes": True}
