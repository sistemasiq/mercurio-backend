from uuid import UUID

import asyncpg

from app.exceptions import Conflicto, NoEncontrado
from app.repositories import paquete_tipos_evento as repo
from app.schemas.paquete_tipos_evento import (
    PaqueteTiposEventoCreate,
    PaqueteTiposEventoOut,
)


async def listar_por_paquete(
    conn: asyncpg.Connection, paquete_id: UUID
) -> list[PaqueteTiposEventoOut]:
    rows = await repo.listar_por_paquete(conn, paquete_id)
    return [PaqueteTiposEventoOut.model_validate(dict(r)) for r in rows]


async def agregar(
    conn: asyncpg.Connection, body: PaqueteTiposEventoCreate
) -> PaqueteTiposEventoOut:
    try:
        row = await repo.agregar(conn, body.paquete_id, body.tipo_evento_id)
    except asyncpg.UniqueViolationError:
        raise Conflicto("El tipo de evento ya está asociado a ese paquete.") from None
    except asyncpg.ForeignKeyViolationError:
        raise NoEncontrado("Paquete o tipo de evento") from None
    return PaqueteTiposEventoOut.model_validate(dict(row))


async def eliminar(conn: asyncpg.Connection, paquete_id: UUID, tipo_evento_id: UUID) -> None:
    resultado = await repo.eliminar(conn, paquete_id, tipo_evento_id)
    if resultado.endswith("0"):
        raise NoEncontrado("Relación paquete-tipo de evento")
