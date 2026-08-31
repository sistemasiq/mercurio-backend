"""
app/models/producto.py
Entidad de dominio — dataclass puro, sin ORM.
Regla 11.1 SAD: prohibido SQLAlchemy en este proyecto.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any


@dataclass
class Producto:
    id: str
    nombre: str
    precio_unitario: Decimal
    tipo: str  # 'A' | 'B' | 'E' | 'S' | 'C'
    sucursal_id: str
    activo: bool = True
    es_combo: bool = False
    descripcion: str | None = None
    imagen: str | None = None
    config_estancia: list[dict[str, Any]] | None = None
    creado: datetime | None = None
    creado_por: str | None = None
    modificado: datetime | None = None
    modificado_por: str | None = None