from __future__ import annotations

from datetime import datetime
from typing import TypedDict
from uuid import UUID

import asyncpg


class SucursalRecord(TypedDict):
    id: UUID
    nombre: str
    direccion: str | None
    telefono: str | None
    correo: str | None
    administrador_id: UUID | None
    administrador_name: str | None
    clave: str | None
    activo: bool
    creado: datetime | None


def _row_to_record(row: asyncpg.Record) -> SucursalRecord:
    return SucursalRecord(
        id=row["id"],
        nombre=row["nombre"],
        direccion=row["direccion"],
        telefono=row["telefono"],
        correo=row["correo"],
        administrador_id=row["administrador_id"],
        administrador_name=row["administrador_name"],
        clave=row["clave"],
        activo=row["activo"],
        creado=row["creado"],
    )


_SELECT = """
    SELECT id, nombre, direccion, telefono, correo,
           administrador_id, administrador_name, clave, activo, creado
    FROM public.sucursales
"""


async def get_all_sucursales(conn: asyncpg.Connection) -> list[SucursalRecord]:
    rows = await conn.fetch(_SELECT + "ORDER BY nombre")
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
    correo: str | None,
    administrador_id: UUID | None,
    administrador_name: str | None,
    clave: str | None,
    creado_por: UUID,
) -> UUID:
    row = await conn.fetchrow(
        """
        INSERT INTO public.sucursales
            (nombre, direccion, telefono, correo, administrador_id, administrador_name, clave, creado_por)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        RETURNING id
        """,
        nombre,
        direccion,
        telefono,
        correo,
        administrador_id,
        administrador_name,
        clave,
        creado_por,
    )
    return UUID(str(row["id"]))


async def update_sucursal(
    conn: asyncpg.Connection,
    clave: UUID,
    nombre: str,
    direccion: str | None,
    telefono: str | None,
    correo: str | None,
    administrador_id: UUID | None,
    administrador_name: str | None,
    modificado_por: UUID,
) -> bool:
    result = await conn.execute(
        """
        UPDATE public.sucursales
        SET nombre = $1, direccion = $2, telefono = $3, correo = $4,
            administrador_id = $5::uuid, administrador_name = $6,
            modificado = NOW(), modificado_por = $7::uuid
        WHERE id = $8::uuid AND activo = TRUE
        """,
        nombre,
        direccion,
        telefono,
        correo,
        administrador_id,
        administrador_name,
        modificado_por,
        sucursal_id,
    )
    return str(result) == "UPDATE 1"


async def deactivate_sucursal(
    conn: asyncpg.Connection, sucursal_id: UUID, modificado_por: UUID
) -> bool:
    result = await conn.execute(
        """
        UPDATE public.sucursales
        SET activo = FALSE, modificado = NOW(), modificado_por = $1
        WHERE id = $2 AND activo = TRUE
        """,
        modificado_por,
        sucursal_id,
    )
    return str(result) == "UPDATE 1"

async def reactivate_sucursal(
    conn: asyncpg.Connection, sucursal_id: UUID, modificado_por: UUID
) -> bool:
    result = await conn.execute(
        """
        UPDATE public.sucursales
        SET activo = TRUE, modificado = NOW(), modificado_por = $1
        WHERE id = $2 AND activo = FALSE
        """,
        modificado_por,
        sucursal_id,
    )
    return str(result) == "UPDATE 1"