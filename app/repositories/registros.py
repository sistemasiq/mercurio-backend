from decimal import Decimal
from enum import Enum
from uuid import UUID

import asyncpg


class EstadoRegistro(str, Enum):
    ACTIVO = "A"
    CERRADO = "C"


async def get_guardian_bracelet_by_detalles_registro_id(
    conn: asyncpg.Connection, registro_id: UUID
) -> UUID | None:
    bracelet_id = await conn.fetchval(
        """
        SELECT pulseras_tutor_id
        FROM registros
        WHERE id = $1 AND activo = TRUE
        """,
        registro_id,
    )

    return UUID(str(bracelet_id)) if bracelet_id is not None else None


async def registro_create(
    conn: asyncpg.Connection,
    registro_id: UUID,
    sucursal_id: UUID,
    tutor_id: UUID,
    pulsera_tutor_id: UUID,
    foto_ine: str,
    foto_llegada: str,
    usuario_id: UUID,
    nombre_segundo_tutor: str | None = None,
    reservacion_id: UUID | None = None,
) -> None:
    await conn.execute(
        """
       INSERT INTO registros (
           id,
           sucursal_id,
           tutores_id,
           nombre_segundo_tutor,
           pulseras_tutor_id,
           foto_ine,
           foto_llegada,
           total,
           estado,
           creado,
           creado_por,
           reservacion_id
       )
       VALUES ($1,$2,$3,$4,$5,$6,$7,0,'P',NOW(),$8,$9)
   """,
        registro_id,
        sucursal_id,
        tutor_id,
        nombre_segundo_tutor,
        pulsera_tutor_id,
        foto_ine,
        foto_llegada,
        usuario_id,
        reservacion_id,
    )


async def registro_update_total(
    conn: asyncpg.Connection, usuario_id: UUID, registro_id: UUID, total: Decimal
) -> None:
    await conn.execute(
        """
        UPDATE registros
        SET total = $1,
            modificado = NOW(),
            modificado_por = $2
        WHERE id = $3
        """,
        total,
        usuario_id,
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
    conn: asyncpg.Connection, estado_nuevo: EstadoRegistro, usuario_id: UUID, registro_id: UUID
) -> None:
    await conn.execute(
        """
        UPDATE registros
        SET estado = $1,
            modificado = NOW(),
            modificado_por = $2
        WHERE id = $3
   """,
        estado_nuevo.value,
        usuario_id,
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

async def exists_registro_any(
    conn: asyncpg.Connection,
    registro_id: UUID,
) -> bool:
    result = await conn.fetchval(
        """
       SELECT 1
       FROM registros
       WHERE id=$1
   """,
        registro_id,
    )
    return bool(result)

async def exists_registro_by_reservacion_id(
    conn: asyncpg.Connection,
    reservacion_id: UUID,
) -> bool:
    result = await conn.fetchval(
        """
       SELECT 1
       FROM registros
       WHERE reservacion_id=$1 AND activo = TRUE
   """,
        reservacion_id,
    )
    return bool(result)


async def contar_ninos_registrados_por_reservacion(
    conn: asyncpg.Connection, reservacion_id: UUID
) -> int:
    total = await conn.fetchval(
        """
        SELECT COUNT(dr.id)
        FROM detalles_registro dr
        JOIN registros r ON r.id = dr.registros_id
        WHERE r.reservacion_id = $1 AND dr.activo = TRUE AND r.activo = TRUE
        """,
        reservacion_id,
    )
    return int(total or 0)
