from uuid import UUID

import asyncpg

from app.exceptions import NoEncontrado
from app.repositories import paquete_tipos_evento_repository
from app.schemas.paquete_tipos_evento import PaqueteTiposEventoCreate, PaqueteTiposEventoOut


async def listar_por_paquete(
    conn: asyncpg.Connection, paquete_id: UUID
) -> list[PaqueteTiposEventoOut]:
    rows = await paquete_tipos_evento_repository.listar_por_paquete(conn, paquete_id)
    return [PaqueteTiposEventoOut.model_validate(r) for r in rows]


async def agregar(
    conn: asyncpg.Connection, body: PaqueteTiposEventoCreate
) -> PaqueteTiposEventoOut:
    row = await paquete_tipos_evento_repository.agregar(
        conn, paquete_id=body.paquete_id, tipo_evento_id=body.tipo_evento_id
    )
    return PaqueteTiposEventoOut.model_validate(row)


async def eliminar(conn: asyncpg.Connection, paquete_id: UUID, tipo_evento_id: UUID) -> None:
    eliminado = await paquete_tipos_evento_repository.eliminar(conn, paquete_id, tipo_evento_id)
    if not eliminado:
        raise NoEncontrado("Relación paquete-tipo de evento")
