from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.comanda import DetalleCreate, EstadoComanda


class PagoIn(BaseModel):
    metodoPagoId: UUID  # noqa: N815 — camelCase requerido por el contrato JSON del frontend
    monto: float


# ---------------------------------------------------------------------------
# DTOs para el endpoint POST /api/pagos/ (pagos_ordenes)
# ---------------------------------------------------------------------------


class PaymentItem(BaseModel):
    metodo_pago_id: UUID
    monto: Decimal = Field(..., gt=0)
    notas_pago: str = ""


class PaymentRequest(BaseModel):
    pagos: list[PaymentItem] = Field(..., min_length=1)
    total_esperado: Decimal = Field(..., gt=0)
    comanda_id: UUID
    sucursal_id: UUID


class PaymentOut(BaseModel):
    id: UUID
    comanda_id: UUID
    metodo_pago_id: UUID
    monto: Decimal
    notas_pago: str | None = None
    sucursal_id: UUID
    creado: datetime
    creado_por: UUID | None = None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# DTO para el endpoint POST /api/pagos/completar (comanda + pago atómico)
# ---------------------------------------------------------------------------


class PagoCompletoRequest(BaseModel):
    """Recibe la comanda y los pagos en un solo request.

    El backend crea la comanda, registra los pagos y notifica a cocina
    en una única transacción. Si falla cualquiera de los dos, nada se
    persiste.
    """

    ticket_numero: str
    total_final: Decimal = Field(..., gt=0)
    detalles_comanda: list[DetalleCreate]
    notas_generales: str | None = None
    pagos: list[PaymentItem] = Field(..., min_length=1)
