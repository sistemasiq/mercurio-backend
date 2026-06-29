from uuid import UUID
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class PagosReservacionBase(BaseModel):
    reservacion_id: UUID
    metodo_pago_id: UUID
    monto: Decimal = Field(..., gt=0)
    notas: str | None = None


class PagosReservacionCreate(PagosReservacionBase): pass


class PagosReservacionUpdate(BaseModel):
    metodo_pago_id: UUID | None = None
    monto: Decimal | None = Field(None, gt=0)
    notas: str | None = None


class PagosReservacionOut(PagosReservacionBase):
    id: UUID
    fecha_pago: datetime
    creado_por: UUID | None = None

    model_config = {'from_attributes': True}
