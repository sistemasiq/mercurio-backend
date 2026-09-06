"""
app/models/caja.py
Entidades de dominio para el módulo de Cierre de Caja — dataclasses puros, sin ORM.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time
from decimal import Decimal
from enum import Enum


class EstadoAperturaCaja(str, Enum):
    ABIERTA = "ABIERTA"
    EN_CORTE = "EN_CORTE"
    CERRADA = "CERRADA"


class ConceptoRetiro(str, Enum):
    PAGO_PROVEEDOR = "Pago a proveedor"
    COMPRA_INSUMOS = "Compra de insumos"
    DEPOSITO_BANCARIO = "Depósito bancario"
    RESGUARDO_EFECTIVO = "Resguardo de efectivo"
    PAGO_SERVICIOS = "Pago de servicios"
    GASTOS_ADMINISTRATIVOS = "Gastos administrativos"
    GASTOS_VARIOS = "Gastos varios"


class TipoDestinatario(str, Enum):
    PROVEEDOR = "Proveedor"
    EMPLEADO = "Empleado"
    ADMINISTRADOR = "Administrador"


class TipoCierreEnum(str, Enum):
    NORMAL = "NORMAL"
    EXTRAORDINARIO = "EXTRAORDINARIO"


class TipoMovimientoCaja(str, Enum):
    ESTANCIA = "E"
    ORDEN = "O"
    RESERVACION = "R"
    RETIRO = "RP"
    CAMBIO = "C"


@dataclass
class Caja:
    id: str
    sucursal_id: str
    codigo: str
    nombre: str
    creado: datetime | None = None
    creado_por: str | None = None
    modificado: datetime | None = None
    modificado_por: str | None = None


@dataclass
class Turno:
    id: str
    nombre: str
    hora_inicio: time
    hora_fin: time
    creado: datetime | None = None
    creado_por: str | None = None
    modificado: datetime | None = None
    modificado_por: str | None = None


@dataclass
class AperturaCaja:
    id: str
    caja_id: str
    cajero_id: str
    turno_id: str
    fondo_inicial: Decimal
    estado: EstadoAperturaCaja = EstadoAperturaCaja.ABIERTA
    conteo_json: str | None = None
    monto_declarado: Decimal | None = None
    token_admin_jti: str | None = None
    creado: datetime | None = None
    creado_por: str | None = None
    modificado: datetime | None = None
    modificado_por: str | None = None
    # Datos complementarios (joins)
    cajero_nombre: str | None = None
    caja_nombre: str | None = None
    sucursal_id: str | None = None
    sucursal_nombre: str | None = None
    turno_nombre: str | None = None


@dataclass
class RetiroParcial:
    id: str
    apertura_caja_id: str
    concepto: ConceptoRetiro
    tipo_destinatario: TipoDestinatario
    monto: Decimal
    observaciones: str | None = None
    creado: datetime | None = None
    creado_por: str | None = None


@dataclass
class MovimientoCaja:
    id: str
    apertura_caja_id: str
    tipo_movimiento: TipoMovimientoCaja
    referencia_id: str
    metodo_pago_id: str
    monto: Decimal
    creado: datetime | None = None
    creado_por: str | None = None
    metodo_pago_nombre: str | None = None


@dataclass
class CierreCaja:
    id: str
    apertura_caja_id: str
    tipo_cierre: TipoCierreEnum
    monto_sistema: Decimal
    monto_cierre: Decimal
    cajero_id: str | None
    fecha_autorizacion_cajero: datetime | None
    administrador_id: str
    fecha_autorizacion_admin: datetime
    observaciones: str | None = None
    creado: datetime | None = None
    creado_por: str | None = None
