from typing import Any
from uuid import UUID

import asyncpg

from app.exceptions import Conflicto, NoEncontrado
from app.repositories import pulseras as pulseras_repository
from app.repositories.pulseras import get_pulseras_disponibles_por_sucursal
from app.schemas.auth import TokenData
from app.schemas.pulseras import PulseraCrear, PulseraOut, PulseraUpdate


async def get_pulseras_disponibles_by_sucursal_id(
    conn: asyncpg.Connection, sucursal_id: UUID
) -> list[dict[str, Any]]:
    return await get_pulseras_disponibles_por_sucursal(conn, sucursal_id)


async def listar_todas(conn: asyncpg.Connection, sucursal_id: UUID) -> list[PulseraOut]:
    rows = await pulseras_repository.listar_todas(conn, sucursal_id)
    return [PulseraOut.model_validate(r) for r in rows]


async def obtener(conn: asyncpg.Connection, pulsera_id: UUID) -> PulseraOut:
    row = await pulseras_repository.obtener(conn, pulsera_id)
    if not row:
        raise NoEncontrado("Pulsera")
    return PulseraOut.model_validate(row)


async def crear(conn: asyncpg.Connection, body: PulseraCrear, current_user: TokenData) -> PulseraOut:
    creado_por = UUID(current_user.sub)
    try:
        row = await pulseras_repository.crear(conn, body.sucursal_id, body.pulsera_rfid, creado_por)
    except asyncpg.UniqueViolationError as exc:
        raise Conflicto("Ya existe una pulsera con ese RFID en esta sucursal.") from exc
    return PulseraOut.model_validate(row)


async def actualizar(conn: asyncpg.Connection, pulsera_id: UUID, body: PulseraUpdate) -> PulseraOut:
    await obtener(conn, pulsera_id)
    updates = body.model_dump(exclude_unset=True)
    try:
        row = await pulseras_repository.actualizar(conn, pulsera_id, updates)
    except asyncpg.UniqueViolationError as exc:
        raise Conflicto("Ya existe una pulsera con ese RFID en esta sucursal.") from exc
    if not row:
        raise NoEncontrado("Pulsera")
    return PulseraOut.model_validate(row)


async def eliminar(conn: asyncpg.Connection, pulsera_id: UUID) -> None:
    await obtener(conn, pulsera_id)
    await pulseras_repository.eliminar(conn, pulsera_id)
