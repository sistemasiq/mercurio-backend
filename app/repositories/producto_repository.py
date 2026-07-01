"""
app/repositories/producto_repository.py
Única capa que habla con la BD para productos — SQL crudo con asyncpg.
Regla 11.1 y 11.4 SAD.
"""

from __future__ import annotations

from decimal import Decimal

import asyncpg

from app.models.producto import Producto


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
    )


async def get_productos_activos(conn: asyncpg.Connection) -> list[Producto]:
    """Retorna todos los productos activos."""
    rows = await conn.fetch(
        """
        SELECT
            id, nombre, precio_unitario, tipo, sucursal_id, activo,
            descripcion, imagen, creado, creado_por, modificado, modificado_por
        FROM public.productos
        WHERE activo = TRUE
        ORDER BY nombre ASC
        """
    )
    return [_row_to_producto(r) for r in rows]
