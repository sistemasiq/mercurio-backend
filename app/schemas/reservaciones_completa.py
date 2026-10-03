"""Shapes para POST /reservaciones/completa (QA #10): alta atómica de la
reservación junto con sus extras, productos y pagos (anticipo) en una sola
transacción -- mismo problema que resolvió pagos_reservacion.completar() para
los cobros, pero para el alta completa."""

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.pagos_reservacion import (
    PagoReservacionItem,
    PagosReservacionOut,
)
from app.schemas.reservacion_extras import ReservacionExtrasOut
from app.schemas.reservacion_productos import ReservacionProductosOut
from app.schemas.reservaciones import ReservacionesCrear, ReservacionesOut


class ReservacionCompletaExtraItem(BaseModel):
    extra_id: UUID
    cantidad: int = Field(..., ge=1)
    precio_unitario: Decimal = Field(..., ge=0)


class ReservacionCompletaProductoItem(BaseModel):
    producto_id: UUID
    cantidad: int = Field(..., ge=1)
    precio_unitario: Decimal = Field(..., ge=0)
    notas: str | None = None


class ReservacionCompletaRequest(BaseModel):
    reservacion: ReservacionesCrear
    extras: list[ReservacionCompletaExtraItem] = Field(default_factory=list)
    productos: list[ReservacionCompletaProductoItem] = Field(default_factory=list)
    pagos: list[PagoReservacionItem] = Field(default_factory=list)
    cambio: Decimal = Field(Decimal("0"), ge=0)


class ReservacionCompletaResponse(BaseModel):
    reservacion: ReservacionesOut
    extras: list[ReservacionExtrasOut]
    productos: list[ReservacionProductosOut]
    pagos: list[PagosReservacionOut]
    cambio: Decimal
    advertencia_efectivo: str | None = None
