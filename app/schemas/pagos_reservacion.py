from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class PagosReservacionBase(BaseModel):
    reservacion_id: UUID
    metodo_pago_id: UUID
    monto: Decimal = Field(..., gt=0)
    notas: str | None = None


class PagosReservacionCreate(PagosReservacionBase):
    pass


class PagoReservacionItem(BaseModel):
    metodo_pago_id: UUID
    monto: Decimal = Field(..., gt=0)
    notas: str | None = None


class PagosReservacionCompletarRequest(BaseModel):
    """Agrupa todos los pagos de un cobro (anticipo o saldo de evento) en una
    sola operación atómica, con el cambio (si lo hay) validado contra el
    efectivo realmente aportado -- arquitectura equivalente a
    PagoCompletoRequest del módulo de comandas/POS."""

    reservacion_id: UUID
    pagos: list[PagoReservacionItem] = Field(..., min_length=1)
    cambio: Decimal = Field(Decimal("0"), ge=0)


class PagosReservacionUpdate(BaseModel):
    metodo_pago_id: UUID | None = None
    monto: Decimal | None = Field(None, gt=0)
    notas: str | None = None


class PagosReservacionOut(PagosReservacionBase):
    id: UUID
    fecha_pago: datetime
    creado_por: UUID | None = None

    model_config = {"from_attributes": True}


class PagosReservacionCompletarResponse(BaseModel):
    pagos: list[PagosReservacionOut]
    cambio: Decimal
