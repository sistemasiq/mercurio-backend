"""
app/services/producto_service.py
Lógica de negocio para productos.
SAD §3.2: el service orquesta repositorios, nunca escribe SQL directamente.
"""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any
from uuid import UUID

import asyncpg
from fastapi import HTTPException, UploadFile, status

from app.core.object_storage import PREFIJOS, upload_bytes, validar_y_leer
from app.core.roles import ROL_SISTEMA
from app.exceptions import NoEncontrado
from app.models.producto import Producto
from app.repositories import combo_repository, producto_repository
from app.schemas.auth import TokenData
from app.schemas.producto import ProductoCrear, ProductoOut, ProductoUpdate


async def _guardar_imagen(producto_id: UUID, imagen: UploadFile) -> str:
    """Sube la imagen del producto a MinIO y retorna su clave (ruta)."""
    extension = Path(imagen.filename or "").suffix.lower() or ".jpg"
    nombre_archivo = f"{producto_id}{extension}"
    data = await validar_y_leer(imagen)
    ruta = f"{PREFIJOS['productos']}/{nombre_archivo}"
    await upload_bytes(ruta, data, imagen.content_type or "image/jpeg")
    return ruta


async def listar_activos(
    conn: asyncpg.Connection, sucursal_id: UUID | None = None
) -> list[Producto]:
    """Retorna los productos activos, filtrados por sucursal si se indica."""
    return await producto_repository.get_productos_activos(conn, sucursal_id)


async def listar_todos(
    conn: asyncpg.Connection, sucursal_id: UUID | None = None
) -> list[ProductoOut]:
    rows = await producto_repository.listar_todos(conn, sucursal_id)
    return [ProductoOut.model_validate(r) for r in rows]


async def obtener(conn: asyncpg.Connection, producto_id: UUID) -> ProductoOut:
    row = await producto_repository.obtener(conn, producto_id)
    if not row:
        raise NoEncontrado("Producto")

    producto_dict = asdict(row)

    if producto_dict.get("tipo") == "C":
        items = await combo_repository.obtener_items_de_combo(conn, producto_id)
        producto_dict["productos_combo"] = items

    return ProductoOut.model_validate(producto_dict)


async def crear(
    conn: asyncpg.Connection,
    body: ProductoCrear,
    usuario_id: UUID | None = None,
    imagen: UploadFile | None = None,
) -> ProductoOut:
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
    row_dict = asdict(row)

    if imagen is not None:
        ruta_imagen = await _guardar_imagen(row_dict["id"], imagen)
        await producto_repository.actualizar(conn, row_dict["id"], {"imagen": ruta_imagen})
        row_dict["imagen"] = ruta_imagen

    if body.tipo == "C" and hasattr(body, "productos_combo") and body.productos_combo:
        items_dict = [item.model_dump() for item in body.productos_combo]
        await combo_repository.asociar_productos_a_combo(
            conn, combo_id=row_dict["id"], items=items_dict, usuario_id=usuario_id
        )

    return ProductoOut.model_validate(row_dict)


async def actualizar(
    conn: asyncpg.Connection,
    producto_id: UUID,
    body: ProductoUpdate,
    usuario_id: UUID | None = None,  # <-- Recibimos usuario_id
    imagen: UploadFile | None = None,
    current_user: TokenData | None = None,
) -> ProductoOut:
    producto_actual = await obtener(conn, producto_id)

    if (
        current_user is not None
        and current_user.role != ROL_SISTEMA
        and str(producto_actual.sucursal_id) != str(current_user.branch_id)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "FORBIDDEN",
                "message": "No puede modificar productos de otra sucursal.",
            },
        )

    updates = body.model_dump(exclude_unset=True)
    productos_combo = updates.pop("productos_combo", None)

    if imagen is not None:
        updates["imagen"] = await _guardar_imagen(producto_id, imagen)

    if usuario_id:
        updates["modificado_por"] = usuario_id

    row = await producto_repository.actualizar(conn, producto_id, updates)
    if not row:
        raise NoEncontrado("Producto")

    row_dict = asdict(row)

    if row_dict.get("tipo") == "C" and productos_combo is not None:
        async with conn.transaction():
            await combo_repository.desasociar_todos_los_productos(
                conn, producto_id, usuario_id=usuario_id
            )
            if productos_combo:
                items_dict = [
                    item.model_dump() if hasattr(item, "model_dump") else dict(item)
                    for item in productos_combo
                ]
                await combo_repository.asociar_productos_a_combo(
                    conn, combo_id=producto_id, items=items_dict, usuario_id=usuario_id
                )

    return await obtener(conn, producto_id)


async def eliminar(
    conn: asyncpg.Connection, producto_id: UUID, usuario_id: UUID | None = None
) -> None:
    await obtener(conn, producto_id)
    await producto_repository.eliminar(conn, producto_id, usuario_id=usuario_id)


async def obtener_productos_para_cajero(
    conn: asyncpg.Connection, current_user: TokenData
) -> list[dict[str, Any]]:
    if current_user.branch_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "BRANCH_REQUIRED", "message": "Sucursal no especificada en el token."},
        )
    return await producto_repository.get_catalogo_venta_by_sucursal(conn, current_user.branch_id)


async def obtener_hijos_combo(conn: asyncpg.Connection, combo_id: UUID) -> list[dict[str, object]]:
    """Retorna los hijos de un combo con sus datos básicos para el carrito."""
    es_combo = await producto_repository.es_producto_combo(conn, combo_id)
    if not es_combo:
        raise NoEncontrado("Combo")

    hijos = await producto_repository.get_combo_hijos(conn, str(combo_id))
    resultado: list[dict[str, object]] = []
    for hijo in hijos:
        producto = await producto_repository.get_by_id(conn, str(hijo["producto_id"]))
        if producto:
            resultado.append(
                {
                    "producto_id": str(hijo["producto_id"]),
                    "nombre": producto["nombre"],
                    "cantidad": hijo["cantidad"],
                    "precio_unitario": float(producto["precio_unitario"]),
                }
            )
    return resultado
