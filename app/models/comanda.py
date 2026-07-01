"""
app/models/comanda.py
Entidades de dominio — dataclasses puros, sin ORM.
Regla 11.1 SAD: prohibido SQLAlchemy en este proyecto.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal


@dataclass
class DetalleComanda:
    id: str
    comanda_id: str
    producto_id: str
    cantidad: int
    precio_unitario: Decimal
    importe: Decimal
    sucursal_id: str
    notas_especiales: str | None = None
    # Nombre del producto (join opcional al leer)
    producto_nombre: str | None = None


@dataclass
class Comanda:
    id: str
    ticket_numero: str
    estado_actual: str  # valor del enum EstadoComanda, ej. 'P'
    total_final: Decimal
    sucursal_id: str
    fecha_hora: datetime | None = None
    detalles: list[DetalleComanda] = field(default_factory=list)
