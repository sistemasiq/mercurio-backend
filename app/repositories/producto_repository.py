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
    id, nombre, precio_unitario, tipo, sucursal_id, activo, es_combo,
    descripcion, imagen, creado, creado_por, modificado, modificado_por
"""


def _row_to_producto(row: asyncpg.Record) -> Producto:
    return Producto(
        id=str(row["id"]),
        nombre=row["nombre"],
        precio_unitario=Decimal(str(row["precio_unitario"])),
        tipo=row["tipo"],
        sucursal_id=str(row["sucursal_id"]),
        activo=row["activo"],
        es_combo=row.get("es_combo", False),
        descripcion=row.get("descripcion"),
        imagen=row.get("imagen"),
        creado=row.get("creado"),
        creado_por=row.get("creado_por"),
        modificado=row.get("modificado"),
        modificado_por=row.get("modificado_por"),
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
    return [dict(r) for r in rows]


async def obtener(conn: asyncpg.Connection, producto_id: UUID) -> dict[str, Any] | None:
    row = await conn.fetchrow(f"SELECT {_COLUMNS} FROM public.productos WHERE id = $1", producto_id)
    return dict(row) if row else None


async def crear(
    conn: asyncpg.Connection,
    nombre: str,
    precio_unitario: Decimal,
    tipo: str,
    sucursal_id: UUID,
    descripcion: str | None,
    imagen: str | None,
    creado_por: UUID | None = None,
) -> dict[str, Any]:
    row = await conn.fetchrow(
        f"""
        INSERT INTO public.productos
            (nombre, precio_unitario, tipo, sucursal_id, descripcion, imagen, creado_por)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        RETURNING {_COLUMNS}
        """,
        nombre,
        precio_unitario,
        tipo,
        sucursal_id,
        descripcion,
        imagen,
        creado_por,
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


async def eliminar(conn: asyncpg.Connection, producto_id: UUID) -> bool:
    result = await conn.execute(
        "UPDATE public.productos SET activo = FALSE, modificado = NOW() "
        "WHERE id = $1 AND activo = TRUE",
        producto_id,
    )
    return bool(result == "UPDATE 1")


async def get_catalogo_venta_by_sucursal(
    conn: asyncpg.Connection, sucursal_id: UUID
) -> list[dict[str, Any]]:
    SQL_CATALOGO = """
        SELECT id, nombre, precio_unitario, descripcion, tipo, imagen, es_combo
        FROM productos
        WHERE sucursal_id = $1
          AND activo = TRUE
          AND (tipo IN ('A', 'B') OR es_combo = TRUE)
        ORDER BY es_combo ASC, nombre
    """
    rows = await conn.fetch(SQL_CATALOGO, sucursal_id)
    return [dict(r) for r in rows]

async def es_producto_combo(conn: asyncpg.Connection, producto_id: UUID) -> bool:
    """
    Verifica si un producto está marcado como combo en la base de datos.
    """
    # Usamos fetchval porque solo esperamos un único valor booleano
    query = "SELECT es_combo FROM productos WHERE id = $1"
    result = await conn.fetchval(query, producto_id)
    
    # Retornamos False si el resultado es None o False
    return result is True

async def get_combo_hijos(conn: asyncpg.Connection, combo_id: str) -> list[dict[str, Any]]:
    rows = await conn.fetch(
        """
        SELECT producto_id, cantidad
        FROM public.producto_combo
        WHERE combo_id = $1
        """,
        combo_id,
    )
    return [dict(row) for row in rows]


async def get_hijos_a_padres_map(conn: asyncpg.Connection) -> dict[str, str]:
    """Retorna un map {producto_hijo_id: nombre_combo_padre} para TODOS los combos."""
    rows = await conn.fetch(
        """
        SELECT pc.producto_id AS hijo_id, p.nombre AS padre_nombre
        FROM public.producto_combo pc
        JOIN public.productos p ON p.id = pc.combo_id
        """
    )
    return {str(r["hijo_id"]): r["padre_nombre"] for r in rows}

async def get_by_id(conn: asyncpg.Connection, producto_id: str):
    return await conn.fetchrow(
        "SELECT * FROM productos WHERE id = $1", 
        producto_id
    )