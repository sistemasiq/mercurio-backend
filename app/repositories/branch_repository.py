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
    creado_por: UUID | None
    creador_name: str | None
    modificado: datetime | None
    modificado_por: UUID | None
    modificador_name: str | None

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
        creado_por=row["creado_por"],
        creador_name=row["creador_name"],
        modificado=row.get("modificado"),
        modificado_por=row.get("modificado_por"),
        modificador_name=row.get("modificador_name"),
    )


# Usamos 'uc' para usuario_creador y 'um' para usuario_modificador
_SELECT = """
    SELECT s.id, s.nombre, s.direccion, s.telefono, s.correo,
           s.administrador_id, s.administrador_name, s.clave, s.activo, 
           s.creado, s.creado_por, uc.nombre_completo AS creador_name,
           s.modificado, s.modificado_por, um.nombre_completo AS modificador_name
    FROM public.sucursales s
    LEFT JOIN public.usuarios uc ON s.creado_por = uc.id
    LEFT JOIN public.usuarios um ON s.modificado_por = um.id
"""


async def get_all_sucursales(conn: asyncpg.Connection) -> list[SucursalRecord]:
    rows = await conn.fetch(_SELECT + " ORDER BY s.nombre")
    return [_row_to_record(r) for r in rows]


async def get_sucursal_by_id(conn: asyncpg.Connection, sucursal_id: UUID) -> SucursalRecord | None:
    row = await conn.fetchrow(_SELECT + " WHERE s.id = $1", sucursal_id)
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
    sucursal_id: UUID,
    clave: str | None,
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
            clave = $7,
            modificado = NOW(), modificado_por = $8::uuid
        WHERE id = $9::uuid AND activo = TRUE
        """,
        nombre,             # $1
        direccion,          # $2
        telefono,           # $3
        correo,             # $4
        administrador_id,   # $5
        administrador_name, # $6
        clave,              # $7
        modificado_por,     # $8
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