from uuid import UUID
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field


class ReservacionExtrasBase(BaseModel):
    reservacion_id:  UUID
    extra_id:        UUID
    cantidad:        int     = Field(..., ge=1)
    precio_unitario: Decimal = Field(..., ge=0)


class ReservacionExtrasCreate(ReservacionExtrasBase): pass


class ReservacionExtrasUpdate(BaseModel):
    cantidad:        int | None     = Field(None, ge=1)
    precio_unitario: Decimal | None = Field(None, ge=0)


class ReservacionExtrasOut(ReservacionExtrasBase):
    id:         UUID
    subtotal:   Decimal
    creado:     datetime
    creado_por: UUID | None

    model_config = {"from_attributes": True}
