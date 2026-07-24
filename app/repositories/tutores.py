from __future__ import annotations

from typing import TypedDict
from uuid import UUID

import asyncpg


class TutorRecord(TypedDict):
    id: UUID
    nombreCompleto: str
    telefono: str


def _tutor_row(row: asyncpg.Record) -> TutorRecord:
    return {
        "id": row["id"],
        "nombreCompleto": row["nombreCompleto"],
        "telefono": row["telefono"],
    }


async def get_tutor_by_phone(
    conn: asyncpg.Connection, telefono: str, sucursal_id: UUID
) -> TutorRecord | None:
    row = await conn.fetchrow(
        """
       SELECT id, nombre_completo AS "nombreCompleto", telefono
       FROM tutores
       WHERE telefono = $1 AND sucursal_id = $2 AND activo = TRUE
   """,
        telefono,
        sucursal_id,
    )

    return _tutor_row(row) if row else None


async def tutor_create(
    conn: asyncpg.Connection,
    sucursal_id: UUID,
    nombre: str,
    telefono: str,
    usuario_id: UUID,
) -> UUID:
    row = await conn.fetchrow(
        """
       INSERT INTO tutores (sucursal_id, nombre_completo, telefono, creado, creado_por)
       VALUES ($1,$2,$3,NOW(),$4)
       RETURNING id
   """,
        sucursal_id,
        nombre,
        telefono,
        usuario_id,
    )

    return UUID(str(row["id"]))
