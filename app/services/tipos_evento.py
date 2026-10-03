from uuid import UUID

import asyncpg

from app.exceptions import Conflicto, NoEncontrado
from app.repositories import tipos_evento_repository
from app.schemas.tipos_evento import TiposEventoCreate, TiposEventoOut, TiposEventoUpdate


async def listar(conn: asyncpg.Connection, sucursal_id: UUID | None = None) -> list[TiposEventoOut]:
    rows = await tipos_evento_repository.listar(conn, sucursal_id)
    return [TiposEventoOut.model_validate(r) for r in rows]


async def obtener(conn: asyncpg.Connection, tipo_evento_id: UUID) -> TiposEventoOut:
    row = await tipos_evento_repository.obtener(conn, tipo_evento_id)
    if not row or not row["activo"]:
        raise NoEncontrado("Tipo de evento")
    return TiposEventoOut.model_validate(row)


async def crear(conn: asyncpg.Connection, body: TiposEventoCreate) -> TiposEventoOut:
    if await tipos_evento_repository.nombre_existe(conn, body.nombre, body.sucursal_id):
        raise Conflicto(f"Ya existe un tipo de evento con el nombre '{body.nombre}'.")
    row = await tipos_evento_repository.crear(
        conn, sucursal_id=body.sucursal_id, nombre=body.nombre, descripcion=body.descripcion
    )
    return TiposEventoOut.model_validate(row)


async def actualizar(
    conn: asyncpg.Connection, tipo_evento_id: UUID, body: TiposEventoUpdate
) -> TiposEventoOut:
    await obtener(conn, tipo_evento_id)
    updates = body.model_dump(exclude_unset=True)
    row = await tipos_evento_repository.actualizar(conn, tipo_evento_id, updates)
    if not row:
        raise NoEncontrado("Tipo de evento")
    return TiposEventoOut.model_validate(row)


async def eliminar(conn: asyncpg.Connection, tipo_evento_id: UUID) -> None:
    await obtener(conn, tipo_evento_id)
    await tipos_evento_repository.eliminar(conn, tipo_evento_id)
