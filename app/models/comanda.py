"""
app/models/comanda.py
Entidades de dominio — dataclasses puros, sin ORM.
Regla 11.1 SAD: prohibido SQLAlchemy en este proyecto.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any


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
    # Datos del producto (join opcional al leer)
    nombre: str | None = None
    producto_nombre: str | None = None
    producto_tipo: str | None = None
    # Origen del combo — persistidos en BD para evitar ambigüedad
    nombre_combo_padre: str | None = None
    es_hijo_de: str | None = None
    es_hijo_combo: bool = False
    # Instancia de combo: agrupa hijos de una misma unidad pedida (KDS)
    id_combo_padre: str | None = None


@dataclass
class Comanda:
    id: str
    ticket_numero: str
    estado_actual: str  # valor del enum EstadoComanda, ej. 'P'
    total_final: Decimal
    sucursal_id: str
    fecha_hora: datetime | None = None
    nombre_cliente: str | None = None
    # expandir_detalles_comanda() reemplaza esta lista por dicts (uno por
    # producto hijo cuando hay combos) — no siempre son DetalleComanda.
    detalles: list[DetalleComanda | dict[str, Any]] = field(default_factory=list)
