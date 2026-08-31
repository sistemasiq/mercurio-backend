from enum import Enum
from typing import List, Dict
from uuid import UUID

import asyncpg

class TipoFoto(str, Enum):
    INE = "I"
    LLEGADA = "L"
async def foto_create(
    conn: asyncpg.Connection,
    registro_id: UUID,
    tipo: TipoFoto,
    storage_url: str,
    usuario_id: UUID,
    id: UUID = None,
) -> None:

    if id is None:
        await conn.execute(
            """
            INSERT INTO fotos (
                registro_id,
                tipo,
                storage_url,
                creado,
                creado_por
            )
            VALUES ($1, $2, $3, NOW(), $4)
            """,
            registro_id,
            tipo,
            storage_url,
            usuario_id,
        )
    else:
        await conn.execute(
            """
            INSERT INTO fotos (
                id,
                registro_id,
                tipo,
                storage_url,
                creado,
                creado_por
            )
            VALUES ($1, $2, $3, $4, NOW(), $5)
            """,
            id,
            registro_id,
            tipo,
            storage_url,
            usuario_id,
        )

async def get_fotos_llegada_by_registro_id(
    conn: asyncpg.Connection,
    registro_id: UUID,
) -> List[Dict]:
    rows = await conn.fetch(
        """
        SELECT storage_url
        FROM fotos
        WHERE registro_id = $1 AND tipo = $2
        """,
        registro_id,
        TipoFoto.LLEGADA.value,
    )
    return [dict(row) for row in rows]