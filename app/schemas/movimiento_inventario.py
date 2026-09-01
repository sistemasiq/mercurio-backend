from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class MovimientoManualCreate(BaseModel):
    tipo: Literal["E", "M"]  # E entrada manual | M merma
    cantidad: Decimal = Field(..., gt=0)
    notas: str | None = None


class ConteoFisicoCreate(BaseModel):
    """Conteo físico: el usuario captura el stock real que ve en el anaquel y el
    sistema calcula el ajuste (entrada si sobra, merma si falta)."""

    stock_contado: Decimal = Field(..., ge=0)
    notas: str | None = None


class CogsRenglonOut(BaseModel):
    insumo_id: UUID
    insumo_nombre: str
    cantidad_salida: Decimal
    costo_total: Decimal

    model_config = {"from_attributes": True}


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
    costo_total: Decimal | None
    creado: datetime
    creado_por: UUID | None

    model_config = {"from_attributes": True}
