from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class ReservacionProductosBase(BaseModel):
    reservacion_id: UUID
    producto_id: UUID
    cantidad: int = Field(..., ge=1)
    precio_unitario: Decimal = Field(..., ge=0)
    notas: str | None = None


class ReservacionProductosCreate(ReservacionProductosBase):
    pass


class ReservacionProductosUpdate(BaseModel):
    cantidad: int | None = Field(None, ge=1)
    precio_unitario: Decimal | None = Field(None, ge=0)
    notas: str | None = None


class ReservacionProductosOut(ReservacionProductosBase):
    id: UUID
    subtotal: Decimal
    creado: datetime
    creado_por: UUID | None

    model_config = {"from_attributes": True}
