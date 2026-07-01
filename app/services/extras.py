from uuid import UUID

import asyncpg

from app.exceptions import NoEncontrado
from app.repositories import extras_repository
from app.schemas.extras import ExtrasCrear, ExtrasOut, ExtrasUpdate


async def listar(conn: asyncpg.Connection, sucursal_id: UUID | None = None) -> list[ExtrasOut]:
    rows = await extras_repository.listar(conn, sucursal_id)
    return [ExtrasOut.model_validate(r) for r in rows]


async def obtener(conn: asyncpg.Connection, extra_id: UUID) -> ExtrasOut:
    row = await extras_repository.obtener(conn, extra_id)
    if not row or not row["activo"]:
        raise NoEncontrado("Extra")
    return ExtrasOut.model_validate(row)


async def crear(conn: asyncpg.Connection, body: ExtrasCrear) -> ExtrasOut:
    row = await extras_repository.crear(
        conn,
        sucursal_id=body.sucursal_id,
        nombre=body.nombre,
        descripcion=body.descripcion,
        precio=body.precio,
        unidad=body.unidad,
    )
    return ExtrasOut.model_validate(row)


async def actualizar(conn: asyncpg.Connection, extra_id: UUID, body: ExtrasUpdate) -> ExtrasOut:
    await obtener(conn, extra_id)
    updates = body.model_dump(exclude_unset=True)
    row = await extras_repository.actualizar(conn, extra_id, updates)
    if not row:
        raise NoEncontrado("Extra")
    return ExtrasOut.model_validate(row)


async def eliminar(conn: asyncpg.Connection, extra_id: UUID) -> None:
    await obtener(conn, extra_id)
    await extras_repository.eliminar(conn, extra_id)
