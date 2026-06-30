from uuid import UUID

import asyncpg

from app.exceptions import Conflicto, NoEncontrado
from app.repositories import tipos_evento as repo
from app.schemas.tipos_evento import TiposEventoCreate, TiposEventoOut, TiposEventoUpdate


async def listar(conn: asyncpg.Connection) -> list[TiposEventoOut]:
    rows = await repo.listar(conn)
    return [TiposEventoOut.model_validate(dict(r)) for r in rows]


async def obtener(conn: asyncpg.Connection, tipo_evento_id: UUID) -> TiposEventoOut:
    row = await repo.obtener_por_id(conn, tipo_evento_id)
    if not row or not row["activo"]:
        raise NoEncontrado("Tipo de evento")
    return TiposEventoOut.model_validate(dict(row))


async def crear(
    conn: asyncpg.Connection, body: TiposEventoCreate, actor_id: UUID | None = None
) -> TiposEventoOut:
    try:
        row = await repo.crear(
            conn, nombre=body.nombre, descripcion=body.descripcion, creado_por=actor_id
        )
    except asyncpg.UniqueViolationError:
        raise Conflicto(f"Ya existe un tipo de evento con el nombre '{body.nombre}'.") from None
    return TiposEventoOut.model_validate(dict(row))


async def actualizar(
    conn: asyncpg.Connection,
    tipo_evento_id: UUID,
    body: TiposEventoUpdate,
    actor_id: UUID | None = None,
) -> TiposEventoOut:
    actual = await obtener(conn, tipo_evento_id)
    cambios = body.model_dump(exclude_unset=True)
    if not cambios:
        return actual
    try:
        row = await repo.actualizar(conn, tipo_evento_id, cambios, modificado_por=actor_id)
    except asyncpg.UniqueViolationError:
        raise Conflicto("Ya existe un tipo de evento con ese nombre.") from None
    assert row is not None  # garantizado por obtener() previo
    return TiposEventoOut.model_validate(dict(row))


async def eliminar(
    conn: asyncpg.Connection, tipo_evento_id: UUID, actor_id: UUID | None = None
) -> None:
    await obtener(conn, tipo_evento_id)
    await repo.desactivar(conn, tipo_evento_id, modificado_por=actor_id)
