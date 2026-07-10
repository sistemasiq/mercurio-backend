"""
app/services/producto_service.py
Lógica de negocio para productos.
SAD §3.2: el service orquesta repositorios, nunca escribe SQL directamente.
"""

from __future__ import annotations

from uuid import UUID

import asyncpg

from app.exceptions import NoEncontrado
from app.models.producto import Producto
from app.repositories import producto_repository, combo_repository
from app.schemas.producto import ProductoCrear, ProductoOut, ProductoUpdate
from dataclasses import asdict

async def listar_activos(conn: asyncpg.Connection) -> list[Producto]:
    """Retorna todos los productos activos."""
    return await producto_repository.get_productos_activos(conn)


async def listar_todos(
    conn: asyncpg.Connection, sucursal_id: UUID | None = None
) -> list[ProductoOut]:
    rows = await producto_repository.listar_todos(conn, sucursal_id)
    return [ProductoOut.model_validate(r) for r in rows]


async def obtener(conn: asyncpg.Connection, producto_id: UUID) -> ProductoOut:
    row = await producto_repository.obtener(conn, producto_id)
    if not row:
        raise NoEncontrado("Producto")

    producto_dict = asdict(row) if hasattr(row, "__dataclass_fields__") else dict(row)

    if producto_dict.get("tipo") == "C":
        items = await combo_repository.obtener_items_de_combo(conn, producto_id)
        producto_dict["productos_combo"] = items

    return ProductoOut.model_validate(producto_dict)

async def crear(conn: asyncpg.Connection, body: ProductoCrear, usuario_id: UUID | None = None) -> ProductoOut:
    row = await producto_repository.crear(
        conn,
        nombre=body.nombre,
        precio_unitario=body.precio_unitario,
        tipo=body.tipo,
        sucursal_id=body.sucursal_id,
        descripcion=body.descripcion,
        imagen=body.imagen,
    )
    row_dict = dict(row) if not hasattr(row, "__dataclass_fields__") else asdict(row)

    if body.tipo == "C" and hasattr(body, "productos_combo") and body.productos_combo:
        items_dict = [item.model_dump() for item in body.productos_combo]
        await combo_repository.asociar_productos_a_combo(
            conn,
            combo_id=row_dict["id"],
            items=items_dict,
            usuario_id=usuario_id
        )

    return ProductoOut.model_validate(row_dict)

async def actualizar(
    conn: asyncpg.Connection, producto_id: UUID, body: ProductoUpdate
) -> ProductoOut:
    await obtener(conn, producto_id)
    updates = body.model_dump(exclude_unset=True)
    row = await producto_repository.actualizar(conn, producto_id, updates)
    if not row:
        raise NoEncontrado("Producto")
    return ProductoOut.model_validate(row)


async def eliminar(conn: asyncpg.Connection, producto_id: UUID) -> None:
    await obtener(conn, producto_id)
    await producto_repository.eliminar(conn, producto_id)
