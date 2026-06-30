from uuid import UUID

import asyncpg

from app.exceptions import NoEncontrado
from app.repositories import sucursal as repo
from app.schemas.sucursal import SucursalCreate, SucursalOut, SucursalUpdate


async def listar(conn: asyncpg.Connection) -> list[SucursalOut]:
    rows = await repo.listar(conn)
    return [SucursalOut.model_validate(dict(r)) for r in rows]


async def obtener(conn: asyncpg.Connection, sucursal_id: UUID) -> SucursalOut:
    row = await repo.obtener_por_id(conn, sucursal_id)
    if not row or not row["activo"]:
        raise NoEncontrado("Sucursal")
    return SucursalOut.model_validate(dict(row))


async def crear(
    conn: asyncpg.Connection, body: SucursalCreate, actor_id: UUID | None = None
) -> SucursalOut:
    row = await repo.crear(
        conn,
        nombre=body.nombre,
        direccion=body.direccion,
        telefono=body.telefono,
        creado_por=actor_id,
    )
    return SucursalOut.model_validate(dict(row))


async def actualizar(
    conn: asyncpg.Connection,
    sucursal_id: UUID,
    body: SucursalUpdate,
    actor_id: UUID | None = None,
) -> SucursalOut:
    actual = await obtener(conn, sucursal_id)
    cambios = body.model_dump(exclude_unset=True)
    if not cambios:
        return actual
    row = await repo.actualizar(conn, sucursal_id, cambios, modificado_por=actor_id)
    assert row is not None  # garantizado por obtener() previo
    return SucursalOut.model_validate(dict(row))


async def eliminar(
    conn: asyncpg.Connection, sucursal_id: UUID, actor_id: UUID | None = None
) -> None:
    await obtener(conn, sucursal_id)
    await repo.desactivar(conn, sucursal_id, modificado_por=actor_id)
