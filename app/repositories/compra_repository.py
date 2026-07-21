"""
app/repositories/compra_repository.py
Única capa que habla con la BD para compras — SQL crudo con asyncpg.
Regla 11.1 y 11.4 SAD.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID

import asyncpg

from app.schemas.compra import DetalleCompraItem

_COLUMNS = """
    c.id, c.sucursal_id, c.proveedor_id, c.estado, c.fecha_pedido, c.fecha_recepcion,
    c.total, c.notas, c.activo, c.creado, c.creado_por, c.modificado, c.modificado_por,
    p.nombre AS proveedor_nombre
"""

_SELECT = f"""
    SELECT {_COLUMNS}
    FROM public.compras c
    JOIN public.proveedores p ON p.id = c.proveedor_id
"""

_DETALLE_SELECT = """
    SELECT dc.id, dc.compra_id, dc.insumo_id, dc.unidad_medida_id, dc.presentacion_id,
           dc.cantidad, dc.costo_unitario, dc.subtotal,
           i.nombre AS insumo_nombre, um.codigo AS unidad_medida_codigo,
           pi.nombre AS presentacion_nombre
    FROM public.detalle_compras dc
    JOIN public.insumos i ON i.id = dc.insumo_id
    LEFT JOIN public.unidades_medida um ON um.id = dc.unidad_medida_id
    LEFT JOIN public.presentaciones_insumo pi ON pi.id = dc.presentacion_id
"""


async def crear_con_detalles(
    conn: asyncpg.Connection,
    sucursal_id: UUID,
    proveedor_id: UUID,
    notas: str | None,
    detalles: list[DetalleCompraItem],
    creado_por: UUID,
) -> UUID:
    total = sum((d.cantidad * d.costo_unitario for d in detalles), Decimal("0"))
    async with conn.transaction():
        compra_id: UUID = await conn.fetchval(
            """
            INSERT INTO public.compras (sucursal_id, proveedor_id, notas, total, creado_por)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING id
            """,
            sucursal_id,
            proveedor_id,
            notas,
            total,
            creado_por,
        )
        for detalle in detalles:
            await conn.execute(
                """
                INSERT INTO public.detalle_compras
                    (compra_id, insumo_id, unidad_medida_id, presentacion_id,
                     cantidad, costo_unitario)
                VALUES ($1, $2, $3, $4, $5, $6)
                """,
                compra_id,
                detalle.insumo_id,
                detalle.unidad_medida_id,
                detalle.presentacion_id,
                detalle.cantidad,
                detalle.costo_unitario,
            )
    return compra_id


async def obtener(conn: asyncpg.Connection, compra_id: UUID) -> dict[str, Any] | None:
    row = await conn.fetchrow(_SELECT + " WHERE c.id = $1", compra_id)
    return dict(row) if row else None


async def listar(conn: asyncpg.Connection, sucursal_id: UUID | None = None) -> list[dict[str, Any]]:
    if sucursal_id:
        rows = await conn.fetch(
            _SELECT + " WHERE c.sucursal_id = $1 ORDER BY c.fecha_pedido DESC", sucursal_id
        )
    else:
        rows = await conn.fetch(_SELECT + " ORDER BY c.fecha_pedido DESC")
    return [dict(r) for r in rows]


async def listar_detalles(conn: asyncpg.Connection, compra_id: UUID) -> list[dict[str, Any]]:
    rows = await conn.fetch(
        _DETALLE_SELECT + " WHERE dc.compra_id = $1 ORDER BY i.nombre ASC", compra_id
    )
    return [dict(r) for r in rows]


async def actualizar(
    conn: asyncpg.Connection, compra_id: UUID, updates: dict[str, Any]
) -> dict[str, Any] | None:
    if not updates:
        return await obtener(conn, compra_id)
    set_parts = [f"{k} = ${i + 2}" for i, k in enumerate(updates)]
    set_parts.append("modificado = NOW()")
    sql = f"UPDATE public.compras SET {', '.join(set_parts)} WHERE id = $1 RETURNING id"
    row = await conn.fetchrow(sql, compra_id, *updates.values())
    return await obtener(conn, compra_id) if row else None


async def marcar_recibida(conn: asyncpg.Connection, compra_id: UUID) -> dict[str, Any] | None:
    """Solo transiciona si el estado actual es 'P' (guard de idempotencia:
    no se puede recibir dos veces ni una compra ya cancelada)."""
    result = await conn.execute(
        """
        UPDATE public.compras
        SET estado = 'R', fecha_recepcion = NOW(), modificado = NOW()
        WHERE id = $1 AND estado = 'P'
        """,
        compra_id,
    )
    if result == "UPDATE 0":
        return None
    return await obtener(conn, compra_id)


async def marcar_cancelada(conn: asyncpg.Connection, compra_id: UUID) -> dict[str, Any] | None:
    result = await conn.execute(
        "UPDATE public.compras SET estado = 'C', modificado = NOW() WHERE id = $1 AND estado = 'P'",
        compra_id,
    )
    if result == "UPDATE 0":
        return None
    return await obtener(conn, compra_id)
