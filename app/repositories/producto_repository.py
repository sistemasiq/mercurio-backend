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
    descripcion, imagen, codigo, config_estancia, creado, creado_por, modificado, modificado_por
"""

# Costo de la receta: suma de cantidad * costo_unitario vigente de cada insumo.
# Un insumo sin costo registrado cuenta como 0; un producto sin receta da NULL.
_COSTO_RECETA = """
    (SELECT SUM(pi.cantidad * COALESCE(i.costo_unitario, 0))
     FROM public.producto_insumos pi
     JOIN public.insumos i ON i.id = pi.insumo_id
     WHERE pi.producto_id = productos.id) AS costo_receta
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
        codigo=row.get("codigo"),
        costo_receta=(
            Decimal(str(row["costo_receta"]))
            if "costo_receta" in row.keys() and row["costo_receta"] is not None
            else None
        ),
        config_estancia=row.get("config_estancia"),
        creado=row.get("creado"),
        creado_por=row.get("creado_por"),
        modificado=row.get("modificado"),
        modificado_por=row.get("modificado_por"),
    )


async def get_productos_activos(
    conn: asyncpg.Connection, sucursal_id: UUID | None = None
) -> list[Producto]:
    """Retorna los productos activos, filtrados por sucursal si se indica."""
    if sucursal_id:
        rows = await conn.fetch(
            f"SELECT {_COLUMNS} FROM public.productos "
            "WHERE activo = TRUE AND sucursal_id = $1 ORDER BY nombre ASC",
            sucursal_id,
        )
    else:
        rows = await conn.fetch(
            f"SELECT {_COLUMNS} FROM public.productos WHERE activo = TRUE ORDER BY nombre ASC"
        )
    return [_row_to_producto(r) for r in rows]


async def listar_todos(conn: asyncpg.Connection, sucursal_id: UUID | None = None) -> list[Producto]:
    """Lista productos (activos e inactivos) para la pantalla de administración."""
    if sucursal_id:
        rows = await conn.fetch(
            f"SELECT {_COLUMNS}, {_COSTO_RECETA} FROM public.productos "
            "WHERE sucursal_id = $1 ORDER BY nombre ASC",
            sucursal_id,
        )
    else:
        rows = await conn.fetch(
            f"SELECT {_COLUMNS}, {_COSTO_RECETA} FROM public.productos ORDER BY nombre ASC"
        )
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
    config_estancia: list[dict] | None = None,
    usuario_id: UUID | None = None,
    codigo: str | None = None,
) -> Producto:
    es_combo = True if tipo == "C" else False

    if tipo == "E":
        row = await conn.fetchrow(
            f"""
            INSERT INTO public.productos
                (nombre, precio_unitario, tipo, sucursal_id, descripcion, imagen, es_combo,
                 config_estancia, creado_por, codigo)
            VALUES ($1, 0, $2, $3, $4, $5, $6, $7, $8, $9)
            RETURNING {_COLUMNS}
            """,
            nombre,
            tipo,
            sucursal_id,
            descripcion,
            imagen,
            es_combo,
            config_estancia,
            usuario_id,
            codigo,
        )
    else:
        row = await conn.fetchrow(
            f"""
            INSERT INTO public.productos
                (nombre, precio_unitario, tipo, sucursal_id, descripcion, imagen, es_combo,
                 creado_por, codigo)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
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
            codigo,
        )
    return _row_to_producto(row)


async def actualizar(
    conn: asyncpg.Connection, producto_id: UUID, updates: dict[str, Any]
) -> Producto | None:
    if not updates:
        return await obtener(conn, producto_id)
    set_parts = [f"{k} = ${i + 2}" for i, k in enumerate(updates)]
    set_parts.append("modificado = NOW()")
    sql = (
        f"UPDATE public.productos SET {', '.join(set_parts)} WHERE id = $1 " f"RETURNING {_COLUMNS}"
    )
    row = await conn.fetchrow(sql, producto_id, *updates.values())
    return _row_to_producto(row) if row else None


async def eliminar(
    conn: asyncpg.Connection, producto_id: UUID, usuario_id: UUID | None = None
) -> bool:
    result = await conn.execute(
        "UPDATE public.productos SET activo = FALSE, modificado = NOW(), modificado_por = $2 "
        "WHERE id = $1 AND activo = TRUE",
        producto_id,
        usuario_id,
    )
    return bool(result == "UPDATE 1")


async def get_catalogo_venta_by_sucursal(
    conn: asyncpg.Connection, sucursal_id: UUID
) -> list[dict[str, Any]]:
    # disponible_estimado (C1 #3): el "rinde" ya existe para la pantalla de
    # Insumos, pero esa consulta exige inventario:ver (el Cajero no lo tiene),
    # así que el catálogo de venta expone su propia estimación — el mínimo de
    # stock_actual / cantidad sobre los insumos de la receta, redondeado hacia
    # abajo. NULL si el producto no tiene receta (producto_insumos vacío).
    sql_catalogo = """
        SELECT
            p.id, p.nombre, p.precio_unitario, p.descripcion, p.tipo, p.imagen, p.es_combo,
            (
                SELECT MIN(FLOOR(i.stock_actual / pi.cantidad))
                FROM public.producto_insumos pi
                JOIN public.insumos i ON i.id = pi.insumo_id
                WHERE pi.producto_id = p.id AND pi.cantidad > 0
            ) AS disponible_estimado
        FROM productos p
        WHERE p.sucursal_id = $1
          AND p.activo = TRUE
          AND (p.tipo IN ('A', 'B') OR p.es_combo = TRUE)
        ORDER BY p.es_combo ASC, p.nombre
    """
    rows = await conn.fetch(sql_catalogo, sucursal_id)
    resultado = []
    for r in rows:
        fila = dict(r)
        if fila["disponible_estimado"] is not None:
            fila["disponible_estimado"] = int(fila["disponible_estimado"])
        resultado.append(fila)
    return resultado


async def es_producto_combo(conn: asyncpg.Connection, producto_id: str | UUID) -> bool:
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
          AND activo = TRUE
        """,
        combo_id,
    )
    return [dict(row) for row in rows]


async def get_by_id(conn: asyncpg.Connection, producto_id: str) -> asyncpg.Record | None:
    return await conn.fetchrow("SELECT * FROM productos WHERE id = $1", producto_id)


async def get_producto_estancia_by_branch_id(conn: asyncpg.Connection, sucursal_id: str):
    row = await conn.fetchrow(
        """
        SELECT id, config_estancia
        FROM productos
        WHERE sucursal_id = $1
          AND activo = TRUE
          AND tipo = 'E'
        LIMIT 1
        """,
        sucursal_id,
    )
    return row if row else None
