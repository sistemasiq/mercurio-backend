from uuid import UUID

import asyncpg

from app.exceptions import NoEncontrado
from app.repositories import metodos_pago_repository
from app.schemas.metodos_pago import MetodosPagoOut, MetodosPagoUpdate


async def listar(conn: asyncpg.Connection, sucursal_id: UUID | None = None) -> list[MetodosPagoOut]:
    rows = await metodos_pago_repository.listar(conn, sucursal_id)
    return [MetodosPagoOut.model_validate(r) for r in rows]


async def obtener(
    conn: asyncpg.Connection, metodo_pago_id: UUID, sucursal_id: UUID | None = None
) -> MetodosPagoOut:
    row = await metodos_pago_repository.obtener(conn, metodo_pago_id, sucursal_id)
    if not row:
        raise NoEncontrado("Método de pago")
    return MetodosPagoOut.model_validate(row)


async def actualizar_catalogo(
    conn: asyncpg.Connection,
    metodo_pago_id: UUID,
    body: MetodosPagoUpdate,
    sucursal_id: UUID | None = None,
) -> MetodosPagoOut:
    if not await metodos_pago_repository.existe(conn, metodo_pago_id):
        raise NoEncontrado("Método de pago")
    updates = body.model_dump(exclude_unset=True)
    if updates:
        await metodos_pago_repository.actualizar_catalogo(conn, metodo_pago_id, updates)
    return await obtener(conn, metodo_pago_id, sucursal_id)


async def set_activacion(
    conn: asyncpg.Connection,
    metodo_pago_id: UUID,
    sucursal_id: UUID,
    activo: bool,
    usuario_id: UUID,
) -> MetodosPagoOut:
    if not await metodos_pago_repository.existe(conn, metodo_pago_id):
        raise NoEncontrado("Método de pago")
    await metodos_pago_repository.set_activacion(
        conn, metodo_pago_id, sucursal_id, activo, usuario_id
    )
    return await obtener(conn, metodo_pago_id, sucursal_id)
