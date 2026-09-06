"""
app/repositories/movimiento_inventario_repository.py
Única capa que habla con la BD para el ledger de movimientos de inventario —
SQL crudo con asyncpg. Regla 11.1 y 11.4 SAD. Tabla append-only: no hay
`actualizar` ni `eliminar` aquí, solo `registrar` + lecturas.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID

import asyncpg

_SELECT = """
    SELECT mi.id, mi.sucursal_id, mi.insumo_id, mi.tipo, mi.cantidad, mi.stock_resultante,
           mi.motivo, mi.referencia_id, mi.notas, mi.costo_total, mi.creado, mi.creado_por,
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
    costo_total: Decimal | None = None,
) -> UUID:
    row = await conn.fetchrow(
        """
        INSERT INTO public.movimientos_inventario
            (sucursal_id, insumo_id, tipo, cantidad, stock_resultante, motivo,
             referencia_id, notas, creado_por, costo_total)
        VALUES ($1, $2, $3, $4, $5, $6::motivo_movimiento_inventario, $7, $8, $9, $10)
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
        costo_total,
    )
    movimiento_id: UUID = row["id"]
    return movimiento_id


async def obtener(conn: asyncpg.Connection, movimiento_id: UUID) -> dict[str, Any] | None:
    row = await conn.fetchrow(_SELECT + " WHERE mi.id = $1", movimiento_id)
    return dict(row) if row else None


async def costo_unitario_venta(
    conn: asyncpg.Connection, comanda_id: UUID, insumo_id: UUID
) -> Decimal | None:
    """Costo unitario al que salió un insumo en una comanda (para revertirlo al
    mismo costo si se cancela). Promedia todos los movimientos 'S' de esa
    comanda para ese insumo. None si no hay dato de costo."""
    valor = await conn.fetchval(
        """
        SELECT SUM(costo_total) / NULLIF(SUM(cantidad), 0)
        FROM public.movimientos_inventario
        WHERE referencia_id = $1 AND insumo_id = $2
          AND motivo = 'venta_comanda' AND costo_total IS NOT NULL
        """,
        comanda_id,
        insumo_id,
    )
    return Decimal(str(valor)) if valor is not None else None


async def listar_por_insumo(
    conn: asyncpg.Connection,
    insumo_id: UUID,
    desde: date | None = None,
    hasta: date | None = None,
) -> list[dict[str, Any]]:
    """Historial de movimientos de un insumo (kardex), opcionalmente acotado
    a un rango de fechas. `hasta` es inclusivo del día completo."""
    conditions = ["mi.insumo_id = $1"]
    params: list[Any] = [insumo_id]
    if desde is not None:
        params.append(desde)
        conditions.append(f"mi.creado >= ${len(params)}")
    if hasta is not None:
        params.append(hasta)
        conditions.append(f"mi.creado < ${len(params)}::date + interval '1 day'")

    where_clause = " AND ".join(conditions)
    rows = await conn.fetch(_SELECT + f" WHERE {where_clause} ORDER BY mi.creado DESC", *params)
    return [dict(r) for r in rows]


async def reporte_cogs(
    conn: asyncpg.Connection,
    sucursal_id: UUID,
    desde: date | None = None,
    hasta: date | None = None,
) -> list[dict[str, Any]]:
    """Costo de lo consumido (salidas de venta + mermas) por insumo en el
    periodo. `hasta` inclusivo del día completo."""
    conditions = ["mi.sucursal_id = $1", "mi.tipo IN ('S', 'M')"]
    params: list[Any] = [sucursal_id]
    if desde is not None:
        params.append(desde)
        conditions.append(f"mi.creado >= ${len(params)}")
    if hasta is not None:
        params.append(hasta)
        conditions.append(f"mi.creado < ${len(params)}::date + interval '1 day'")

    where_clause = " AND ".join(conditions)
    rows = await conn.fetch(
        f"""
        SELECT mi.insumo_id, i.nombre AS insumo_nombre,
               SUM(mi.cantidad) AS cantidad_salida,
               COALESCE(SUM(mi.costo_total), 0) AS costo_total
        FROM public.movimientos_inventario mi
        JOIN public.insumos i ON i.id = mi.insumo_id
        WHERE {where_clause}
        GROUP BY mi.insumo_id, i.nombre
        ORDER BY costo_total DESC, i.nombre ASC
        """,
        *params,
    )
    return [dict(r) for r in rows]
