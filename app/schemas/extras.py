from uuid import UUID
from datetime import datetime
from typing import Literal
from decimal import Decimal

from pydantic import BaseModel, Field


class ExtrasBase(BaseModel):
    nombre: str = Field(..., max_length=150)
    descripcion: str | None = None
    precio: Decimal = Field(..., ge=0)
    unidad: Literal['evento', 'persona', 'hora'] = 'evento'


class ExtrasCrear(ExtrasBase):
    sucursal_id: UUID | None = None  # None = extra global


class ExtrasUpdate(BaseModel):
    nombre: str | None = None
    descripcion: str | None = None
    precio: Decimal | None = None
    unidad: Literal['evento', 'persona', 'hora'] | None = None
    sucursal_id: UUID | None = None
    activo: bool | None = None


class ExtrasOut(ExtrasBase):
    id: UUID
    sucursal_id: UUID | None
    activo: bool
    creado: datetime
    creado_por: UUID | None
    modificado: datetime | None
    modificado_por: UUID | None

    model_config = {'from_attributes': True}
