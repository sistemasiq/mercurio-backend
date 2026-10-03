from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, field_serializer, field_validator, model_validator

from app.schemas.comanda import DetalleCreate


class PagoIn(BaseModel):
    metodoPagoId: UUID  # noqa: N815 — camelCase requerido por el contrato JSON del frontend
    monto: float = Field(..., gt=0)


class PagoEstanciaExtraRequest(BaseModel):
    pagos: list[PagoIn] = Field(..., min_length=1)
    cambio: Decimal = Field(Decimal("0"), ge=0)


# ---------------------------------------------------------------------------
# DTOs para el endpoint POST /api/pagos/ (pagos_ordenes)
# ---------------------------------------------------------------------------


class PaymentItem(BaseModel):
    metodo_pago_id: UUID
    monto: Decimal = Field(..., gt=0)
    notas_pago: str = ""
    # B9 B.1: últimos 4 dígitos de la tarjeta, opcionales (solo aplica a pagos
    # con tarjeta; para efectivo/transferencia se deja en None).
    ultimos4: str | None = Field(default=None)

    @field_validator("ultimos4")
    @staticmethod
    def _validar_ultimos4(v: str | None) -> str | None:
        if v is None or v == "":
            return None
        if not v.isdigit() or len(v) != 4:
            raise ValueError("ultimos4 debe contener exactamente 4 dígitos.")
        return v


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
    ultimos4: str | None = None
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

    # QA #21: el backend asigna el folio secuencial (folio_repository) dentro de
    # la transacción del cobro. Este campo queda opcional y solo se usa como
    # fallback si por algún motivo no hay folio disponible — el front ya no
    # necesita generar un ticket_numero (ver CajaComponent.vue). max_length=10
    # coincide con comandas.ticket_numero VARCHAR(10) en BD.
    ticket_numero: str | None = Field(default=None, max_length=10)
    total_final: Decimal = Field(..., gt=0)
    detalles_comanda: list[DetalleCreate]
    notas_generales: str | None = None
    pagos: list[PaymentItem] = Field(..., min_length=1)
    celular_cliente: str | None = None
    # max_length=150 coincide con comandas.nombre_cliente VARCHAR(150) en BD —
    # sin esto, un valor más largo tronaba con un 500 crudo de Postgres en vez
    # de un 422 limpio (mismo criterio que AbrirTurnoPayload.terminal).
    nombre_cliente: str | None = Field(default=None, max_length=150)
    # B9 B.2: mesa del pedido, opcional. max_length=20 coincide con
    # comandas.mesa VARCHAR(20) en BD.
    mesa: str | None = Field(default=None, max_length=20)
    puntos_a_redimir: int = Field(0, ge=0)
    cambio: Decimal = Field(Decimal("0"), ge=0)

    @field_validator("celular_cliente")
    @staticmethod
    def _validar_celular(v: str | None) -> str | None:
        if v is None or v == "":
            return None
        if not v.isdigit() or len(v) != 10:
            raise ValueError("El celular debe tener exactamente 10 dígitos.")
        return v

    @model_validator(mode="after")
    def _requiere_celular_para_redimir(self) -> "PagoCompletoRequest":
        if self.puntos_a_redimir > 0 and not self.celular_cliente:
            raise ValueError("Debes indicar celular_cliente para redimir puntos.")
        return self


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
    tipo_origen: str
    referencia_id: UUID
    titulo: str
    total_final: Decimal
    estado_actual: str
    sucursal_id: UUID
    creado: datetime
    creado_por: UUID | None = None
    metodos_pago: list[MetodoPagoResumen]
    # Campos de compatibilidad: solo se llenan para ventas tipo comanda.
    comanda_id: UUID | None = None
    ticket_numero: str | None = None

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
    # QA #34: agrupa los hijos de una misma instancia de combo (migración 038).
    # None para productos sueltos o cuando el dato no existe (estancias/reservaciones).
    id_combo_padre: str | None = None


class MetodoPagoDetalle(BaseModel):
    metodo_pago_nombre: str
    monto: float
    notas_pago: str | None = None
    ultimos4: str | None = None


class DetalleOrdenOut(BaseModel):
    tipo_origen: str = "comanda"
    referencia_id: str
    titulo: str
    total_final: float
    estado_actual: str
    fecha_hora: str | None = None
    motivo_cancelacion: str | None = None
    creado_por_nombre: str | None = None
    metodos_pago: list[MetodoPagoDetalle]
    detalles: list[DetalleProductoOut]
    # Campos de compatibilidad: solo se llenan para ventas tipo comanda.
    comanda_id: str | None = None
    ticket_numero: str | None = None
    # B9 B.3: puntos de lealtad otorgados por esta comanda (join a
    # movimientos_puntos); null si no aplica (no hubo celular, o el origen no
    # es comanda).
    puntos_ganados: int | None = None
    # B9 B.2: mesa del pedido, opcional (solo aplica a comandas).
    mesa: str | None = None


# ---------------------------------------------------------------------------
# DTO para el endpoint GET /api/pagos/estadisticas
# ---------------------------------------------------------------------------


class EstadisticasOut(BaseModel):
    total_ventas: float
    total_ordenes: int
    ticket_promedio: float = 0.0

    model_config = {"from_attributes": True}
