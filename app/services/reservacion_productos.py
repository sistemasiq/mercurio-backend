from uuid import UUID

import asyncpg
from fastapi import HTTPException, status

from app.core.scope import sucursal_scope
from app.exceptions import NoEncontrado
from app.repositories import reservacion_productos_repository, reservaciones_repository
from app.schemas.auth import TokenData
from app.schemas.reservacion_productos import (
    ReservacionProductosCreate,
    ReservacionProductosOut,
    ReservacionProductosUpdate,
)


async def listar_por_reservacion(
    conn: asyncpg.Connection, reservacion_id: UUID, current_user: TokenData
) -> list[ReservacionProductosOut]:
    reservacion = await reservaciones_repository.obtener(conn, reservacion_id)
    if not reservacion:
        raise NoEncontrado("Reservación")

    scope = sucursal_scope(current_user)
    if scope is not None and str(reservacion["sucursal_id"]) != scope:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No puede consultar productos de reservaciones de otra sucursal.",
        )

    rows = await reservacion_productos_repository.listar_por_reservacion(conn, reservacion_id)
    return [ReservacionProductosOut.model_validate(r) for r in rows]


async def obtener(
    conn: asyncpg.Connection, reservacion_producto_id: UUID
) -> ReservacionProductosOut:
    row = await reservacion_productos_repository.obtener(conn, reservacion_producto_id)
    if not row:
        raise NoEncontrado("Producto de reservación")
    return ReservacionProductosOut.model_validate(row)


async def crear(
    conn: asyncpg.Connection, body: ReservacionProductosCreate, current_user: TokenData
) -> ReservacionProductosOut:
    row = await reservacion_productos_repository.crear(
        conn,
        reservacion_id=body.reservacion_id,
        producto_id=body.producto_id,
        cantidad=body.cantidad,
        precio_unitario=body.precio_unitario,
        notas=body.notas,
        creado_por=UUID(current_user.sub),
    )
    return ReservacionProductosOut.model_validate(row)


async def actualizar(
    conn: asyncpg.Connection, reservacion_producto_id: UUID, body: ReservacionProductosUpdate
) -> ReservacionProductosOut:
    await obtener(conn, reservacion_producto_id)
    updates = body.model_dump(exclude_unset=True)
    row = await reservacion_productos_repository.actualizar(conn, reservacion_producto_id, updates)
    if not row:
        raise NoEncontrado("Producto de reservación")
    return ReservacionProductosOut.model_validate(row)


async def eliminar(conn: asyncpg.Connection, reservacion_producto_id: UUID) -> None:
    await obtener(conn, reservacion_producto_id)
    await reservacion_productos_repository.eliminar(conn, reservacion_producto_id)
