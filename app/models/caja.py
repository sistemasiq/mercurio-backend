"""
app/models/caja.py
Entidades de dominio para el módulo de Cierre de Caja — dataclasses puros, sin ORM.
Regla 11.1 SAD: prohibido SQLAlchemy en este proyecto.
"""

from __future__ import annotations

from dataclasses import dataclass, field
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


@dataclass
class Caja:
    id: str
    id_sucursal: str
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
    id_caja: str
    id_usuario: str
    id_turno: str
    monto_inicial: Decimal
    estado: EstadoAperturaCaja = EstadoAperturaCaja.ABIERTA
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
    id_apertura_caja: str
    concepto: ConceptoRetiro
    tipo_destinatario: TipoDestinatario
    monto: Decimal
    observaciones: str | None = None
    creado: datetime | None = None
    creado_por: str | None = None
    modificado: datetime | None = None
    modificado_por: str | None = None


@dataclass
class MovimientoCaja:
    id: str
    id_apertura_caja: str
    tipo_movimiento: TipoMovimientoCaja
    id_referencia: str
    id_metodo_pago: str
    monto: Decimal
    creado: datetime | None = None
    creado_por: str | None = None
    modificado: datetime | None = None
    modificado_por: str | None = None
    metodo_pago_nombre: str | None = None


@dataclass
class CierreCaja:
    id: str
    id_apertura_caja: str
    tipo_cierre: TipoCierreEnum
    monto_sistema: Decimal
    monto_cierre: Decimal
    id_usuario_cajero: str | None
    fecha_autorizacion_cajero: datetime | None
    id_usuario_admin: str
    fecha_autorizacion_admin: datetime
    observaciones: str | None = None
    creado: datetime | None = None
    creado_por: str | None = None
    modificado: datetime | None = None
    modificado_por: str | None = None
