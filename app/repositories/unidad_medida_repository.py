"""
app/repositories/unidad_medida_repository.py
Catálogo global de unidades de medida (fase 1 de inventario). Sembrado por
migración, sin CRUD desde la API — solo lectura para poblar selects al crear
un insumo.
"""

from typing import Any
from uuid import UUID

import asyncpg

_SELECT = """
    SELECT id, codigo, nombre, tipo, factor_a_base, activo
    FROM unidades_medida
"""


async def listar(conn: asyncpg.Connection) -> list[dict[str, Any]]:
    rows = await conn.fetch(_SELECT + " WHERE activo = TRUE ORDER BY tipo, factor_a_base")
    return [dict(r) for r in rows]


async def obtener(conn: asyncpg.Connection, unidad_medida_id: UUID) -> dict[str, Any] | None:
    """Usado por insumo_service para validar que unidad_base y unidad_compra
    compartan el mismo `tipo` antes de crear o actualizar un insumo."""
    row = await conn.fetchrow(_SELECT + " WHERE id = $1", unidad_medida_id)
    return dict(row) if row else None
