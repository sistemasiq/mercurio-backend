from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class RecetaItemUpdate(BaseModel):
    cantidad: Decimal = Field(..., gt=0)


class RecetaItemOut(BaseModel):
    producto_id: UUID
    insumo_id: UUID
    cantidad: Decimal
    insumo_nombre: str
    unidad_base_codigo: str

    model_config = {"from_attributes": True}
