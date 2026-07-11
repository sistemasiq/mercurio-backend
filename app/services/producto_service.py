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
        usuario_id=usuario_id,
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
    conn: asyncpg.Connection, producto_id: UUID, body: ProductoUpdate, usuario_id: UUID | None = None # <-- Recibimos usuario_id
) -> ProductoOut:
    await obtener(conn, producto_id)

    updates = body.model_dump(exclude_unset=True)
    productos_combo = updates.pop("productos_combo", None)

    if usuario_id:
        updates["modificado_por"] = usuario_id

    row = await producto_repository.actualizar(conn, producto_id, updates)
    if not row:
        raise NoEncontrado("Producto")

    row_dict = dict(row) if not hasattr(row, "__dataclass_fields__") else asdict(row)

    if row_dict.get("tipo") == "C" and productos_combo is not None:
        async with conn.transaction():
            await combo_repository.desasociar_todos_los_productos(conn, producto_id)
            if productos_combo:
                items_dict = [
                    item.model_dump() if hasattr(item, "model_dump") else dict(item)
                    for item in productos_combo
                ]
                await combo_repository.asociar_productos_a_combo(
                    conn,
                    combo_id=producto_id,
                    items=items_dict,
                    usuario_id=usuario_id
                )

    return await obtener(conn, producto_id)

async def eliminar(conn: asyncpg.Connection, producto_id: UUID, usuario_id: UUID | None = None) -> None:
    await obtener(conn, producto_id)
    await producto_repository.eliminar(conn, producto_id, usuario_id=usuario_id)
