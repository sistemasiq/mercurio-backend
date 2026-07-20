"""
app/repositories/insumo_repository.py
Única capa que habla con la BD para insumos — SQL crudo con asyncpg.
Regla 11.1 y 11.4 SAD.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID

import asyncpg

_COLUMNS = """
    id, sucursal_id, nombre, descripcion, unidad_base_id, unidad_compra_id,
    stock_actual, stock_minimo, costo_unitario, proveedor_principal_id,
    activo, creado, creado_por, modificado, modificado_por
"""


async def listar(conn: asyncpg.Connection, sucursal_id: UUID | None = None) -> list[dict[str, Any]]:
    """Lista insumos (activos e inactivos), para la pantalla de administración.
    Sin sucursal_id devuelve de todas las sucursales (uso de AdministradorSistema)."""
    if sucursal_id:
        rows = await conn.fetch(
            f"SELECT {_COLUMNS} FROM public.insumos WHERE sucursal_id = $1 ORDER BY nombre ASC",
            sucursal_id,
        )
    else:
        rows = await conn.fetch(f"SELECT {_COLUMNS} FROM public.insumos ORDER BY nombre ASC")
    return [dict(r) for r in rows]


async def obtener(conn: asyncpg.Connection, insumo_id: UUID) -> dict[str, Any] | None:
    row = await conn.fetchrow(f"SELECT {_COLUMNS} FROM public.insumos WHERE id = $1", insumo_id)
    return dict(row) if row else None


async def crear(
    conn: asyncpg.Connection,
    sucursal_id: UUID,
    nombre: str,
    descripcion: str | None,
    unidad_base_id: UUID,
    unidad_compra_id: UUID,
    stock_inicial: Decimal,
    stock_minimo: Decimal,
    costo_unitario: Decimal | None,
    proveedor_principal_id: UUID | None,
    creado_por: UUID,
) -> dict[str, Any]:
    row = await conn.fetchrow(
        f"""
        INSERT INTO public.insumos
            (sucursal_id, nombre, descripcion, unidad_base_id, unidad_compra_id,
             stock_actual, stock_minimo, costo_unitario, proveedor_principal_id, creado_por)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
        RETURNING {_COLUMNS}
        """,
        sucursal_id,
        nombre,
        descripcion,
        unidad_base_id,
        unidad_compra_id,
        stock_inicial,
        stock_minimo,
        costo_unitario,
        proveedor_principal_id,
        creado_por,
    )
    return dict(row)


async def actualizar(
    conn: asyncpg.Connection, insumo_id: UUID, updates: dict[str, Any]
) -> dict[str, Any] | None:
    if not updates:
        return await obtener(conn, insumo_id)
    set_parts = [f"{k} = ${i + 2}" for i, k in enumerate(updates)]
    set_parts.append("modificado = NOW()")
    sql = f"UPDATE public.insumos SET {', '.join(set_parts)} WHERE id = $1 RETURNING {_COLUMNS}"
    row = await conn.fetchrow(sql, insumo_id, *updates.values())
    return dict(row) if row else None


async def eliminar(conn: asyncpg.Connection, insumo_id: UUID) -> bool:
    result = await conn.execute(
        "UPDATE public.insumos SET activo = FALSE, modificado = NOW() "
        "WHERE id = $1 AND activo = TRUE",
        insumo_id,
    )
    return bool(result == "UPDATE 1")
