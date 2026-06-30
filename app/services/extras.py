from uuid import UUID

import asyncpg

from app.exceptions import NoEncontrado
from app.repositories import extras as repo
from app.schemas.extras import ExtrasCrear, ExtrasOut, ExtrasUpdate


async def listar(conn: asyncpg.Connection, sucursal_id: UUID | None = None) -> list[ExtrasOut]:
    rows = await repo.listar(conn, sucursal_id)
    return [ExtrasOut.model_validate(dict(r)) for r in rows]


async def obtener(conn: asyncpg.Connection, extra_id: UUID) -> ExtrasOut:
    row = await repo.obtener_por_id(conn, extra_id)
    if not row or not row["activo"]:
        raise NoEncontrado("Extra")
    return ExtrasOut.model_validate(dict(row))


async def crear(
    conn: asyncpg.Connection, body: ExtrasCrear, actor_id: UUID | None = None
) -> ExtrasOut:
    row = await repo.crear(
        conn,
        sucursal_id=body.sucursal_id,
        nombre=body.nombre,
        descripcion=body.descripcion,
        precio=body.precio,
        unidad=body.unidad,
        creado_por=actor_id,
    )
    return ExtrasOut.model_validate(dict(row))


async def actualizar(
    conn: asyncpg.Connection,
    extra_id: UUID,
    body: ExtrasUpdate,
    actor_id: UUID | None = None,
) -> ExtrasOut:
    actual = await obtener(conn, extra_id)
    cambios = body.model_dump(exclude_unset=True)
    if not cambios:
        return actual
    row = await repo.actualizar(conn, extra_id, cambios, modificado_por=actor_id)
    assert row is not None  # garantizado por obtener() previo
    return ExtrasOut.model_validate(dict(row))


async def eliminar(conn: asyncpg.Connection, extra_id: UUID, actor_id: UUID | None = None) -> None:
    await obtener(conn, extra_id)
    await repo.desactivar(conn, extra_id, modificado_por=actor_id)
