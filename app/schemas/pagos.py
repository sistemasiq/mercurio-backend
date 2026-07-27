from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, field_serializer, field_validator

from app.schemas.comanda import DetalleCreate


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
    celular_cliente: str | None = None

    @field_validator("celular_cliente")
    @staticmethod
    def _validar_celular(v: str | None) -> str | None:
        if v is None or v == "":
            return None
        if not v.isdigit() or len(v) != 10:
            raise ValueError("El celular debe tener exactamente 10 dígitos.")
        return v


# ---------------------------------------------------------------------------
# DTO para el endpoint GET /api/pagos/historial
# ---------------------------------------------------------------------------


class MetodoPagoResumen(BaseModel):
    metodo_pago_id: UUID
    metodo_pago_nombre: str
    monto: Decimal
    notas_pago: str | None = None

    @field_serializer("monto")
    @staticmethod
    def _decimal_to_float(v: Decimal) -> float:
        return float(v)


class HistorialOut(BaseModel):
    comanda_id: UUID
    ticket_numero: str
    total_final: Decimal
    estado_actual: str
    sucursal_id: UUID
    creado: datetime
    creado_por: UUID | None = None
    metodos_pago: list[MetodoPagoResumen]

    model_config = {"from_attributes": True}

    @field_serializer("total_final")
    @staticmethod
    def _decimal_to_float(v: Decimal) -> float:
        return float(v)


# ---------------------------------------------------------------------------
# DTOs para el endpoint GET /api/pagos/detalles/{comanda_id}
# ---------------------------------------------------------------------------


class DetalleProductoOut(BaseModel):
    id: str
    producto_nombre: str
    cantidad: int
    precio_unitario: float
    importe: float
    notas_especiales: str | None = None
    nombre_combo_padre: str | None = None


class MetodoPagoDetalle(BaseModel):
    metodo_pago_nombre: str
    monto: float
    notas_pago: str | None = None


class DetalleOrdenOut(BaseModel):
    comanda_id: str
    ticket_numero: str
    total_final: float
    estado_actual: str
    fecha_hora: str | None = None
    motivo_cancelacion: str | None = None
    creado_por_nombre: str | None = None
    metodos_pago: list[MetodoPagoDetalle]
    detalles: list[DetalleProductoOut]


# ---------------------------------------------------------------------------
# DTO para el endpoint GET /api/pagos/estadisticas
# ---------------------------------------------------------------------------


class EstadisticasOut(BaseModel):
    total_ventas: float
    total_ordenes: int
    ticket_promedio: float = 0.0

    model_config = {"from_attributes": True}
