from __future__ import annotations

from typing import TypedDict
from uuid import UUID

import asyncpg


class SucursalRecord(TypedDict):
    id: UUID
    nombre: str
    direccion: str | None
    telefono: str | None
    activo: bool


def _row_to_record(row: asyncpg.Record) -> SucursalRecord:
    return SucursalRecord(
        id=row["id"],
        nombre=row["nombre"],
        direccion=row["direccion"],
        telefono=row["telefono"],
        activo=row["activo"],
    )


_SELECT = """
    SELECT id, nombre, direccion, telefono, activo
    FROM public.sucursales
"""


async def get_all_sucursales(conn: asyncpg.Connection) -> list[SucursalRecord]:
    rows = await conn.fetch(_SELECT + "WHERE activo = TRUE ORDER BY nombre")
    return [_row_to_record(r) for r in rows]


async def get_sucursal_by_id(conn: asyncpg.Connection, sucursal_id: UUID) -> SucursalRecord | None:
    row = await conn.fetchrow(_SELECT + "WHERE id = $1", sucursal_id)
    return _row_to_record(row) if row else None


async def nombre_exists(conn: asyncpg.Connection, nombre: str) -> bool:
    row = await conn.fetchrow("SELECT id FROM public.sucursales WHERE nombre = $1", nombre)
    return row is not None


async def create_sucursal(
    conn: asyncpg.Connection,
    nombre: str,
    direccion: str | None,
    telefono: str | None,
    creado_por: UUID,
) -> UUID:
    row = await conn.fetchrow(
        """
        INSERT INTO public.sucursales (nombre, direccion, telefono, creado_por)
        VALUES ($1, $2, $3, $4)
        RETURNING id
        """,
        nombre,
        direccion,
        telefono,
        creado_por,
    )
    return UUID(str(row["id"]))
