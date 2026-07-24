"""
app/services/receta_producto_service.py
Lógica de negocio para la receta (BOM) de productos.
SAD §3.2: el service orquesta repositorios, nunca escribe SQL directamente.
"""

from __future__ import annotations

from uuid import UUID

import asyncpg

from app.exceptions import DatosInvalidos, NoEncontrado
from app.repositories import insumo_repository, producto_insumo_repository, producto_repository
from app.schemas.receta_producto import RecetaItemOut, RecetaItemUpdate


async def listar(conn: asyncpg.Connection, producto_id: UUID) -> list[RecetaItemOut]:
    producto = await producto_repository.obtener(conn, producto_id)
    if not producto:
        raise NoEncontrado("Producto")
    rows = await producto_insumo_repository.listar_por_producto(conn, producto_id)
    return [RecetaItemOut.model_validate(r) for r in rows]


async def upsert(
    conn: asyncpg.Connection, producto_id: UUID, insumo_id: UUID, body: RecetaItemUpdate
) -> RecetaItemOut:
    producto = await producto_repository.obtener(conn, producto_id)
    if not producto:
        raise NoEncontrado("Producto")
    insumo = await insumo_repository.obtener(conn, insumo_id)
    if not insumo:
        raise NoEncontrado("Insumo")
    if str(insumo["sucursal_id"]) != producto.sucursal_id:
        raise DatosInvalidos("El insumo no pertenece a la misma sucursal del producto.")
    await producto_insumo_repository.upsert(conn, producto_id, insumo_id, body.cantidad)
    row = await producto_insumo_repository.obtener(conn, producto_id, insumo_id)
    if not row:
        raise RuntimeError("Error al recuperar la línea de receta recién guardada")
    return RecetaItemOut.model_validate(row)


async def eliminar(conn: asyncpg.Connection, producto_id: UUID, insumo_id: UUID) -> None:
    eliminado = await producto_insumo_repository.eliminar(conn, producto_id, insumo_id)
    if not eliminado:
        raise NoEncontrado("Insumo en la receta")
