from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, field_serializer

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


# ---------------------------------------------------------------------------
# DTO para el endpoint GET /api/pagos/historial
# ---------------------------------------------------------------------------


class HistorialOut(BaseModel):
    id: UUID
    comanda_id: UUID
    ticket_numero: str
    total_final: Decimal
    estado_actual: str
    metodo_pago_id: UUID
    metodo_pago_nombre: str
    monto: Decimal
    notas_pago: str | None = None
    sucursal_id: UUID
    creado: datetime
    creado_por: UUID | None = None

    model_config = {"from_attributes": True}

    @field_serializer("monto", "total_final")
    @staticmethod
    def _decimal_to_float(v: Decimal) -> float:
        return float(v)


# ---------------------------------------------------------------------------
# DTOs para el endpoint GET /api/pagos/detalles/{id}
# ---------------------------------------------------------------------------


class DetalleProductoOut(BaseModel):
    producto_nombre: str
    cantidad: int
    precio_unitario: float
    importe: float
    notas_especiales: str | None = None
    nombre_combo_padre: str | None = None


class DetalleOrdenOut(BaseModel):
    pago_id: str
    pago_monto: float
    pago_notas: str | None = None
    pago_creado: str | None = None
    ticket_numero: str
    total_final: float
    estado_actual: str
    fecha_hora: str | None = None
    metodo_pago_nombre: str
    creado_por_nombre: str | None = None
    detalles: list[DetalleProductoOut]


# ---------------------------------------------------------------------------
# DTO para el endpoint GET /api/pagos/estadisticas
# ---------------------------------------------------------------------------


class EstadisticasOut(BaseModel):
    total_ventas: float
    total_ordenes: int
    ticket_promedio: float = 0.0

    model_config = {"from_attributes": True}
