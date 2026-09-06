"""
app/repositories/producto_insumo_repository.py
Única capa que habla con la BD para la receta de productos — SQL crudo con
asyncpg. Regla 11.1 y 11.4 SAD.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID

import asyncpg

_SELECT = """
    SELECT pi.producto_id, pi.insumo_id, pi.cantidad,
           i.nombre AS insumo_nombre, um.codigo AS unidad_base_codigo
    FROM public.producto_insumos pi
    JOIN public.insumos i ON i.id = pi.insumo_id
    JOIN public.unidades_medida um ON um.id = i.unidad_base_id
"""


async def listar_por_producto(conn: asyncpg.Connection, producto_id: UUID) -> list[dict[str, Any]]:
    rows = await conn.fetch(
        _SELECT + " WHERE pi.producto_id = $1 ORDER BY i.nombre ASC", producto_id
    )
    return [dict(r) for r in rows]


async def listar_por_sucursal(conn: asyncpg.Connection, sucursal_id: UUID) -> list[dict[str, Any]]:
    """Receta inversa de todos los insumos activos de la sucursal: qué productos
    A/B activos los consumen y en qué cantidad. Base para la columna "rinde para"
    de la pantalla de insumos. Los combos ('C') no tienen receta directa y quedan
    fuera."""
    rows = await conn.fetch(
        """
        SELECT pi.insumo_id, pi.producto_id, pi.cantidad, p.nombre AS producto_nombre
        FROM public.producto_insumos pi
        JOIN public.insumos i   ON i.id = pi.insumo_id
        JOIN public.productos p ON p.id = pi.producto_id
        WHERE i.sucursal_id = $1 AND i.activo = TRUE
          AND p.activo = TRUE AND p.tipo IN ('A', 'B')
        ORDER BY i.nombre ASC, p.nombre ASC
        """,
        sucursal_id,
    )
    return [dict(r) for r in rows]


async def obtener(
    conn: asyncpg.Connection, producto_id: UUID, insumo_id: UUID
) -> dict[str, Any] | None:
    row = await conn.fetchrow(
        _SELECT + " WHERE pi.producto_id = $1 AND pi.insumo_id = $2", producto_id, insumo_id
    )
    return dict(row) if row else None


async def upsert(
    conn: asyncpg.Connection,
    producto_id: UUID,
    insumo_id: UUID,
    cantidad: Decimal,
    usuario_id: UUID,
) -> None:
    await conn.execute(
        """
        INSERT INTO public.producto_insumos (producto_id, insumo_id, cantidad, creado_por)
        VALUES ($1, $2, $3, $4)
        ON CONFLICT (producto_id, insumo_id) DO UPDATE
        SET cantidad = EXCLUDED.cantidad,
            modificado = now(),
            modificado_por = $4
        """,
        producto_id,
        insumo_id,
        cantidad,
        usuario_id,
    )


async def eliminar(conn: asyncpg.Connection, producto_id: UUID, insumo_id: UUID) -> bool:
    result = await conn.execute(
        "DELETE FROM public.producto_insumos WHERE producto_id = $1 AND insumo_id = $2",
        producto_id,
        insumo_id,
    )
    return bool(result == "DELETE 1")
