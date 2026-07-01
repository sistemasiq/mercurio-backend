from uuid import UUID

import asyncpg

from app.exceptions import NoEncontrado
from app.repositories import paquetes_repository
from app.schemas.paquetes import PaquetesCreate, PaquetesOut, PaquetesUpdate


async def listar(conn: asyncpg.Connection, sucursal_id: UUID | None = None) -> list[PaquetesOut]:
    rows = await paquetes_repository.listar(conn, sucursal_id)
    return [PaquetesOut.model_validate(r) for r in rows]


async def obtener(conn: asyncpg.Connection, paquete_id: UUID) -> PaquetesOut:
    row = await paquetes_repository.obtener(conn, paquete_id)
    if not row or not row["activo"]:
        raise NoEncontrado("Paquete")
    return PaquetesOut.model_validate(row)


async def crear(conn: asyncpg.Connection, body: PaquetesCreate) -> PaquetesOut:
    row = await paquetes_repository.crear(
        conn,
        sucursal_id=body.sucursal_id,
        nombre=body.nombre,
        descripcion=body.descripcion,
        duracion_minutos=body.duracion_minutos,
        personas_incluidas=body.personas_incluidas,
        precio_base=body.precio_base,
        precio_persona_extra=body.precio_persona_extra,
    )
    return PaquetesOut.model_validate(row)


async def actualizar(
    conn: asyncpg.Connection, paquete_id: UUID, body: PaquetesUpdate
) -> PaquetesOut:
    await obtener(conn, paquete_id)
    updates = body.model_dump(exclude_unset=True)
    row = await paquetes_repository.actualizar(conn, paquete_id, updates)
    if not row:
        raise NoEncontrado("Paquete")
    return PaquetesOut.model_validate(row)


async def eliminar(conn: asyncpg.Connection, paquete_id: UUID) -> None:
    await obtener(conn, paquete_id)
    await paquetes_repository.eliminar(conn, paquete_id)
