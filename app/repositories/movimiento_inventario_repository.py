"""
app/repositories/movimiento_inventario_repository.py
Única capa que habla con la BD para el ledger de movimientos de inventario —
SQL crudo con asyncpg. Regla 11.1 y 11.4 SAD. Tabla append-only: no hay
`actualizar` ni `eliminar` aquí, solo `registrar` + lecturas.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID

import asyncpg

_SELECT = """
    SELECT mi.id, mi.sucursal_id, mi.insumo_id, mi.tipo, mi.cantidad, mi.stock_resultante,
           mi.motivo, mi.referencia_id, mi.notas, mi.creado, mi.creado_por,
           i.nombre AS insumo_nombre
    FROM public.movimientos_inventario mi
    JOIN public.insumos i ON i.id = mi.insumo_id
"""


async def registrar(
    conn: asyncpg.Connection,
    *,
    sucursal_id: UUID,
    insumo_id: UUID,
    tipo: str,
    cantidad: Decimal,
    stock_resultante: Decimal,
    motivo: str,
    referencia_id: UUID | None,
    notas: str | None,
    creado_por: UUID | None,
) -> UUID:
    row = await conn.fetchrow(
        """
        INSERT INTO public.movimientos_inventario
            (sucursal_id, insumo_id, tipo, cantidad, stock_resultante, motivo,
             referencia_id, notas, creado_por)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        RETURNING id
        """,
        sucursal_id,
        insumo_id,
        tipo,
        cantidad,
        stock_resultante,
        motivo,
        referencia_id,
        notas,
        creado_por,
    )
    movimiento_id: UUID = row["id"]
    return movimiento_id


async def obtener(conn: asyncpg.Connection, movimiento_id: UUID) -> dict[str, Any] | None:
    row = await conn.fetchrow(_SELECT + " WHERE mi.id = $1", movimiento_id)
    return dict(row) if row else None


async def listar_por_insumo(conn: asyncpg.Connection, insumo_id: UUID) -> list[dict[str, Any]]:
    rows = await conn.fetch(_SELECT + " WHERE mi.insumo_id = $1 ORDER BY mi.creado DESC", insumo_id)
    return [dict(r) for r in rows]
