"""
app/schemas/caja.py
Esquemas Pydantic para el módulo de Cierre de Caja, Apertura, Retiros y Catálogos.
"""

from datetime import datetime, time
from decimal import Decimal
from pydantic import BaseModel, Field
from app.models.caja import (
    EstadoAperturaCaja,
    ConceptoRetiro,
    TipoDestinatario,
    TipoCierreEnum,
    TipoMovimientoCaja,
)

# ── Catálogos: Caja y Turno ─────────────

class CajaCreate(BaseModel):
    id_sucursal: str
    codigo: str
    nombre: str


class CajaResponse(BaseModel):
    id: str
    id_sucursal: str
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


# ── Apertura de Caja ────────────────────

class AbrirTurnoPayload(BaseModel):
    fondo_inicial: Decimal = Field(..., ge=0)
    # max_length=20 coincide con cajas.codigo VARCHAR(20) en BD — sin esto, un valor
    # más largo tronaba con un 500 crudo de Postgres en vez de un 422 limpio.
    terminal: str | None = Field(default="CAJA 01", max_length=20)
    observaciones_apertura: str | None = None
    id_caja: str | None = None
    id_turno: str | None = None
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
    movimientos: list[MovimientoResumen] = []


# ── Retiros Parciales ───────────────────

class RetiroParcialCreate(BaseModel):
    id_apertura_caja: str
    concepto: ConceptoRetiro = ConceptoRetiro.GASTOS_VARIOS
    tipo_destinatario: TipoDestinatario
    monto: Decimal = Field(..., gt=0)
    observaciones: str | None = None


class RetiroParcialResponse(BaseModel):
    id: str
    id_apertura_caja: str
    concepto: ConceptoRetiro
    tipo_destinatario: TipoDestinatario
    monto: Decimal
    observaciones: str | None = None
    creado: datetime


# ── Declaración de Conteo y Arqueo ─────

class DenominacionCantidad(BaseModel):
    denominacion: Decimal
    cantidad: int


class DesgloseEfectivoPayload(BaseModel):
    billetes: list[DenominacionCantidad] = []
    monedas: list[DenominacionCantidad] = []
    total: Decimal


class MetodoPagoMonto(BaseModel):
    metodo: str
    monto: Decimal


class ConteoPayload(BaseModel):
    turno_id: str
    desglose_efectivo: DesgloseEfectivoPayload
    metodos_pago: list[MetodoPagoMonto]
    total_declarado: Decimal


# ── Autenticación / Revisión Admin ──────

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


# ── Confirmación de Cierre y PDF ───────

class ConfirmarCierrePayload(BaseModel):
    turno_id: str
    observaciones: str | None = None
    tipo_cierre: TipoCierreEnum = TipoCierreEnum.NORMAL


class ConfirmarCierreResponse(BaseModel):
    arqueo_id: str
    estado: str
    pdf_url: str | None = None
    mensaje: str = "Cierre confirmado."


# ── Historial y Consultas ──────────────

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
    observaciones: str | None = ""
