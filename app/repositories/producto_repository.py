"""
app/repositories/producto_repository.py
Única capa que habla con la BD para productos — SQL crudo con asyncpg.
Regla 11.1 y 11.4 SAD.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID

import asyncpg

from app.models.producto import Producto

_COLUMNS = """
    id, nombre, precio_unitario, tipo, sucursal_id, activo,
    descripcion, imagen, creado, creado_por, modificado, modificado_por, es_combo
"""


def _row_to_producto(row: asyncpg.Record) -> Producto:
    return Producto(
        id=str(row["id"]),
        nombre=row["nombre"],
        precio_unitario=Decimal(str(row["precio_unitario"])),
        tipo=row["tipo"],
        sucursal_id=str(row["sucursal_id"]),
        activo=row["activo"],
        descripcion=row.get("descripcion"),
        imagen=row.get("imagen"),
        creado=row.get("creado"),
        creado_por=row.get("creado_por"),
        modificado=row.get("modificado"),
        modificado_por=row.get("modificado_por"),
        es_combo=row.get("es_combo"),
    )


async def get_productos_activos(conn: asyncpg.Connection) -> list[Producto]:
    """Retorna todos los productos activos."""
    rows = await conn.fetch(
        f"SELECT {_COLUMNS} FROM public.productos WHERE activo = TRUE ORDER BY nombre ASC"
    )
    return [_row_to_producto(r) for r in rows]


async def listar_todos(
    conn: asyncpg.Connection, sucursal_id: UUID | None = None
) -> list[dict[str, Any]]:
    """Lista productos (activos e inactivos) para la pantalla de administración."""
    if sucursal_id:
        rows = await conn.fetch(
            f"SELECT {_COLUMNS} FROM public.productos WHERE sucursal_id = $1 ORDER BY nombre ASC",
            sucursal_id,
        )
    else:
        rows = await conn.fetch(f"SELECT {_COLUMNS} FROM public.productos ORDER BY nombre ASC")
    return [_row_to_producto(r) for r in rows]


async def obtener(conn: asyncpg.Connection, producto_id: UUID) -> Producto | None:
    row = await conn.fetchrow(f"SELECT {_COLUMNS} FROM public.productos WHERE id = $1", producto_id)
    return _row_to_producto(row) if row else None


async def crear(
    conn: asyncpg.Connection,
    nombre: str,
    precio_unitario: Decimal,
    tipo: str,
    sucursal_id: UUID,
    descripcion: str | None,
    imagen: str | None,
    usuario_id: UUID | None = None,
) -> dict[str, Any]:
    es_combo = True if tipo == "C" else False

    row = await conn.fetchrow(
        f"""
        INSERT INTO public.productos
            (nombre, precio_unitario, tipo, sucursal_id, descripcion, imagen, es_combo, creado_por)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        RETURNING {_COLUMNS}
        """,
        nombre,
        precio_unitario,
        tipo,
        sucursal_id,
        descripcion,
        imagen,
        es_combo,
        usuario_id,
    )
    return dict(row)

async def actualizar(
    conn: asyncpg.Connection, producto_id: UUID, updates: dict[str, Any]
) -> dict[str, Any] | None:
    if not updates:
        return await obtener(conn, producto_id)
    set_parts = [f"{k} = ${i + 2}" for i, k in enumerate(updates)]
    set_parts.append("modificado = NOW()")
    sql = (
        f"UPDATE public.productos SET {', '.join(set_parts)} WHERE id = $1 " f"RETURNING {_COLUMNS}"
    )
    row = await conn.fetchrow(sql, producto_id, *updates.values())
    return dict(row) if row else None


async def eliminar(conn: asyncpg.Connection, producto_id: UUID, usuario_id: UUID | None = None) -> bool:
    result = await conn.execute(
        "UPDATE public.productos SET activo = FALSE, modificado = NOW(), modificado_por = $2 "
        "WHERE id = $1 AND activo = TRUE",
        producto_id,
        usuario_id,
    )
    return bool(result == "UPDATE 1")
