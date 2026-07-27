from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class MovimientoManualCreate(BaseModel):
    tipo: Literal["E", "M"]  # E entrada manual | M merma
    cantidad: Decimal = Field(..., gt=0)
    notas: str | None = None


class MovimientoInventarioOut(BaseModel):
    id: UUID
    sucursal_id: UUID
    insumo_id: UUID
    insumo_nombre: str
    tipo: str
    cantidad: Decimal
    stock_resultante: Decimal
    motivo: str
    referencia_id: UUID | None
    notas: str | None
    creado: datetime
    creado_por: UUID | None

    model_config = {"from_attributes": True}
