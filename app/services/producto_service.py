"""
app/services/producto_service.py
Lógica de negocio para productos.
SAD §3.2: el service orquesta repositorios, nunca escribe SQL directamente.
"""

from __future__ import annotations

from uuid import UUID

import asyncpg
from fastapi import HTTPException, status

from app.exceptions import NoEncontrado
from app.repositories import producto_repository
from app.schemas.producto import ProductoCrear, ProductoOut, ProductoUpdate
from app.schemas.auth import TokenData


async def listar_todos(
    conn: asyncpg.Connection, sucursal_id: UUID | None = None
) -> list[ProductoOut]:
    rows = await producto_repository.listar_todos(conn, sucursal_id)
    return [ProductoOut.model_validate(r) for r in rows]


async def obtener(conn: asyncpg.Connection, producto_id: UUID) -> ProductoOut:
    row = await producto_repository.obtener(conn, producto_id)
    if not row:
        raise NoEncontrado("Producto")
    return ProductoOut.model_validate(row)


async def crear(conn: asyncpg.Connection, body: ProductoCrear, creado_por: UUID | None = None) -> ProductoOut:
    row = await producto_repository.crear(
        conn,
        nombre=body.nombre,
        precio_unitario=body.precio_unitario,
        tipo=body.tipo,
        sucursal_id=body.sucursal_id,
        descripcion=body.descripcion,
        imagen=body.imagen,
        creado_por=creado_por,
    )
    return ProductoOut.model_validate(row)


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


async def obtener_productos_para_cajero(conn: asyncpg.Connection, current_user: TokenData):
    if current_user.branch_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "BRANCH_REQUIRED", "message": "Sucursal no especificada en el token."},
        )
    return await producto_repository.get_catalogo_venta_by_sucursal(conn, current_user.branch_id)

async def expandir_detalles_comanda(conn, detalles):
    """
    Función reutilizable: Convierte detalles con combos en detalles individuales.
    Funciona igual para guardar en BD o para mostrar en pantalla.
    """
    detalles_expandidos = []
    for item in detalles:
        if await producto_repository.es_producto_combo(conn, item.producto_id):
            hijos = await producto_repository.get_combo_hijos(conn, item.producto_id)
            for hijo in hijos:
                hijo_producto = await producto_repository.get_by_id(conn, str(hijo["producto_id"]))
                nombre_hijo = hijo_producto["nombre"] if hijo_producto else ""
                detalles_expandidos.append({
                    "producto_id": str(hijo["producto_id"]),
                    "nombre": nombre_hijo,
                    "cantidad": hijo["cantidad"] * item.cantidad,
                    "es_hijo_de": item.producto_id
                })
        else:
            detalles_expandidos.append(item.dict())
    return detalles_expandidos

