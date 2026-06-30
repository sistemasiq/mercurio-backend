from uuid import UUID

import asyncpg

from app.exceptions import NoEncontrado
from app.repositories import paquetes as repo
from app.schemas.paquetes import PaquetesCreate, PaquetesOut, PaquetesUpdate


async def listar(conn: asyncpg.Connection, sucursal_id: UUID | None = None) -> list[PaquetesOut]:
    rows = await repo.listar(conn, sucursal_id)
    return [PaquetesOut.model_validate(dict(r)) for r in rows]


async def obtener(conn: asyncpg.Connection, paquete_id: UUID) -> PaquetesOut:
    row = await repo.obtener_por_id(conn, paquete_id)
    if not row or not row["activo"]:
        raise NoEncontrado("Paquete")
    return PaquetesOut.model_validate(dict(row))


async def crear(
    conn: asyncpg.Connection, body: PaquetesCreate, actor_id: UUID | None = None
) -> PaquetesOut:
    row = await repo.crear(
        conn,
        sucursal_id=body.sucursal_id,
        nombre=body.nombre,
        descripcion=body.descripcion,
        duracion_minutos=body.duracion_minutos,
        personas_incluidas=body.personas_incluidas,
        precio_base=body.precio_base,
        precio_persona_extra=body.precio_persona_extra,
        creado_por=actor_id,
    )
    return PaquetesOut.model_validate(dict(row))


async def actualizar(
    conn: asyncpg.Connection,
    paquete_id: UUID,
    body: PaquetesUpdate,
    actor_id: UUID | None = None,
) -> PaquetesOut:
    actual = await obtener(conn, paquete_id)
    cambios = body.model_dump(exclude_unset=True)
    if not cambios:
        return actual
    row = await repo.actualizar(conn, paquete_id, cambios, modificado_por=actor_id)
    assert row is not None  # garantizado por obtener() previo
    return PaquetesOut.model_validate(dict(row))


async def eliminar(
    conn: asyncpg.Connection, paquete_id: UUID, actor_id: UUID | None = None
) -> None:
    await obtener(conn, paquete_id)
    await repo.desactivar(conn, paquete_id, modificado_por=actor_id)
