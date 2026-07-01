from decimal import Decimal
from enum import Enum
from uuid import UUID

import asyncpg


class EstadoRegistro(str, Enum):
    ACTIVO = "A"
    CERRADO = "C"


async def registro_create(
    conn: asyncpg.Connection,
    registro_id: UUID,
    sucursal_id: UUID,
    tutor_id: UUID,
    foto_ine: str,
    foto_llegada: str,
    usuario_id: UUID,
) -> None:
    await conn.execute(
        """
       INSERT INTO registros (
           id,
           sucursal_id,
           tutores_id,
           foto_ine,
           foto_llegada,
           total,
           estado,
           creado_por
       )
       VALUES ($1,$2,$3,$4,$5,0,'P',$6)
   """,
        registro_id,
        sucursal_id,
        tutor_id,
        foto_ine,
        foto_llegada,
        usuario_id,
    )


async def registro_update_total(
    conn: asyncpg.Connection, registro_id: UUID, total: Decimal
) -> None:
    await conn.execute(
        """
       UPDATE registros SET total = $1 WHERE id = $2
   """,
        total,
        registro_id,
    )


async def registro_add_total(
    conn: asyncpg.Connection, total_extra: float, usuario_id: UUID, registro_id: UUID
) -> None:
    await conn.execute(
        """
                   UPDATE registros
                   SET total = total + $1,
                       modificado = NOW(),
                       modificado_por = $2
                   WHERE id = $3
               """,
        total_extra,
        usuario_id,
        registro_id,
    )


async def change_registro_estado(
    conn: asyncpg.Connection, estado_nuevo: EstadoRegistro, registro_id: UUID
) -> None:
    await conn.execute(
        """
       UPDATE registros SET estado = $1 WHERE id = $2
   """,
        estado_nuevo.value,
        registro_id,
    )


async def exists_registro(
    conn: asyncpg.Connection,
    registro_id: UUID,
) -> bool:
    result = await conn.fetchval(
        """
       SELECT 1
       FROM registros
       WHERE id=$1 AND activo = TRUE
   """,
        registro_id,
    )
    return bool(result)
