"""
app/schemas/caja.py
Esquemas Pydantic para el módulo de Cierre de Caja, Apertura, Retiros y Catálogos.
"""

import uuid
from datetime import datetime, time
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

from app.models.caja import (
    ConceptoRetiro,
    TipoCierreEnum,
    TipoDestinatario,
)


def _validar_uuid(v: str) -> str:
    """Valida formato UUID en el borde de la API. Sin esto, un valor mal
    formado llega tal cual a uuid.UUID(...) en caja_repository y truena con
    un 500 crudo en vez de un 422 limpio (mismo patrón ya usado en
    ComandaModifyRequest._validate_uuids)."""
    try:
        uuid.UUID(v)
    except ValueError as exc:
        raise ValueError(f"apertura_caja_id inválido: '{v}'. Se esperaba un UUID válido.") from exc
    return v


# ── Catálogos: Caja y Turno ─────────────────────────────────────────────────


class CajaCreate(BaseModel):
    sucursal_id: str
    codigo: str
    nombre: str


class CajaResponse(BaseModel):
    id: str
    sucursal_id: str
    codigo: str
    nombre: str
    creado: datetime | None = None


class TurnoCreate(BaseModel):
    nombre: str
    hora_inicio: time
    hora_fin: time


class TurnoResponse(BaseModel):
    id: str
    nombre: str
    hora_inicio: time
    hora_fin: time


# ── Apertura de Caja ────────────────────────────────────────────────────────


class AbrirTurnoPayload(BaseModel):
    fondo_inicial: Decimal = Field(..., ge=0)
    # max_length=20 coincide con cajas.codigo VARCHAR(20) en BD — sin esto, un valor
    # más largo tronaba con un 500 crudo de Postgres en vez de un 422 limpio.
    terminal: str | None = Field(default="CAJA 01", max_length=20)
    observaciones_apertura: str | None = None
    caja_id: str | None = None
    turno_id: str | None = None
    # Solo relevante para AdministradorSistema, que no tiene sucursal propia en el JWT.
    sucursal_id: str | None = None


class MovimientoResumen(BaseModel):
    metodo: str
    total_ventas: Decimal


class TurnoActivoResponse(BaseModel):
    id: str
    sucursal_id: str
    sucursal_nombre: str
    cajero_id: str
    cajero_nombre: str
    terminal: str
    estado: str
    fondo_inicial: Decimal
    fecha_apertura: str
    total_ventas: Decimal = Decimal("0")
    total_retiros: Decimal = Decimal("0")
    total_ingresos: Decimal = Decimal("0")
    movimientos: list[MovimientoResumen] = []


# ── Retiros Parciales ───────────────────────────────────────────────────────


class RetiroParcialCreate(BaseModel):
    apertura_caja_id: str
    concepto: ConceptoRetiro = ConceptoRetiro.GASTOS_VARIOS
    tipo_destinatario: TipoDestinatario
    monto: Decimal = Field(..., gt=0)
    observaciones: str | None = None

    _validar_apertura_caja_id = field_validator("apertura_caja_id")(_validar_uuid)


class RetiroParcialResponse(BaseModel):
    id: str
    apertura_caja_id: str
    concepto: ConceptoRetiro
    tipo_destinatario: TipoDestinatario
    monto: Decimal
    observaciones: str | None = None
    creado: datetime


class CambioResponse(BaseModel):
    id: str
    monto: Decimal
    creado: datetime


class IngresoDetalle(BaseModel):
    id: str
    monto: Decimal
    creado: datetime


class IngresoEfectivoCreate(BaseModel):
    apertura_caja_id: str
    monto: Decimal = Field(..., gt=0)

    _validar_apertura_caja_id = field_validator("apertura_caja_id")(_validar_uuid)


class IngresoEfectivoResponse(BaseModel):
    id: str
    apertura_caja_id: str
    monto: Decimal
    creado: datetime


# ── Declaración de Conteo y Arqueo ──────────────────────────────────────────


class DenominacionCantidad(BaseModel):
    denominacion: Decimal = Field(..., gt=0)
    cantidad: int = Field(..., ge=0)


class DesgloseEfectivoPayload(BaseModel):
    billetes: list[DenominacionCantidad] = []
    monedas: list[DenominacionCantidad] = []
    total: Decimal = Field(..., ge=0)


class MetodoPagoMonto(BaseModel):
    metodo: str
    monto: Decimal = Field(..., ge=0)


class ConteoPayload(BaseModel):
    turno_id: str
    desglose_efectivo: DesgloseEfectivoPayload
    metodos_pago: list[MetodoPagoMonto]
    total_declarado: Decimal = Field(..., ge=0)


# ── Autenticación / Revisión Admin ──────────────────────────────────────────


class RevisionAdminPayload(BaseModel):
    turno_id: str
    admin_email: str
    admin_password: str
    pin_hash: str | None = None


class FilaBalance(BaseModel):
    metodo: str
    label: str
    declarado: Decimal
    esperado: Decimal
    diferencia: Decimal


class RevisionAdminResponse(BaseModel):
    autorizado: bool
    admin_nombre: str
    total_esperado: Decimal
    total_declarado: Decimal
    diferencia_neta: Decimal
    balance_por_metodo: list[FilaBalance]


# ── Confirmación de Cierre ──────────────────────────────────────────────────


class ConfirmarCierrePayload(BaseModel):
    turno_id: str
    observaciones: str | None = None
    tipo_cierre: TipoCierreEnum = TipoCierreEnum.NORMAL


class ConfirmarCierreResponse(BaseModel):
    arqueo_id: str
    estado: str
    pdf_url: str | None = None
    mensaje: str = "Cierre confirmado."


# ── Historial y Consultas ───────────────────────────────────────────────────


class FiltrosHistorial(BaseModel):
    sucursal_id: str | None = None
    cajero_id: str | None = None
    fecha_desde: str | None = None
    fecha_hasta: str | None = None
    page: int = 1
    page_size: int = 20


class ArqueoResumen(BaseModel):
    id: str
    cajero_nombre: str
    terminal: str
    sucursal_nombre: str
    fecha_apertura: str
    fecha_cierre: str
    fondo_inicial: Decimal
    total_declarado: Decimal
    total_esperado: Decimal
    diferencia_neta: Decimal
    tiene_observaciones: bool = False
    pdf_url: str | None = None
    admin_nombre: str | None = None
    tipo_cierre: str = "NORMAL"


class HistorialArqueosResponse(BaseModel):
    items: list[ArqueoResumen]
    total: int
    page: int
    page_size: int


class DesgloseEfectivoDetalle(BaseModel):
    billetes: list[dict] = []
    monedas: list[dict] = []
    total: Decimal


class DetalleArqueoResponse(ArqueoResumen):
    desglose_efectivo: DesgloseEfectivoDetalle | None = None
    balance_por_metodo: list[FilaBalance] = []
    retiros: list[RetiroParcialResponse] = []
    cambios: list[CambioResponse] = []
    ingresos: list[IngresoDetalle] = []
    observaciones: str | None = ""


# ── Métodos de Pago del Turno Activo ───────────────────────────────────────


class MetodoPagoTurnoResponse(BaseModel):
    id: str
    nombre: str
