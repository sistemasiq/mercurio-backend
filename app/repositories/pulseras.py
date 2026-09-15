from typing import Any
from uuid import UUID

import asyncpg

from app.schemas.pulseras import PulseraResponse

_COLUMNS = """
    p.id,
    p.sucursal_id,
    p.pulsera_rfid,
    p.activo,
    p.numero_lote,
    p.creado,
    p.creado_por,
    p.modificado,
    p.modificado_por,
    (
        EXISTS (
            SELECT 1
            FROM public.detalles_registro dr
            WHERE dr.pulseras_id = p.id
        )
        OR EXISTS (
            SELECT 1
            FROM public.registros r
            WHERE r.pulseras_tutor_id = p.id
        )
    ) AS usada
"""


async def contar_activas_por_sucursal(conn: asyncpg.Connection, sucursal_id: UUID) -> int:
    """Total de pulseras activas y todavía disponibles de una sucursal.

    Como son desechables, una pulsera asignada a un niño o tutor ya no cuenta
    para la capacidad de un evento futuro.
    """
    total = await conn.fetchval(
        """
        SELECT count(*)
        FROM public.pulseras p
        WHERE p.sucursal_id = $1
          AND p.activo = TRUE
          AND NOT EXISTS (
              SELECT 1
              FROM public.detalles_registro dr
              WHERE dr.pulseras_id = p.id
          )
          AND NOT EXISTS (
              SELECT 1
              FROM public.registros r
              WHERE r.pulseras_tutor_id = p.id
          )
        """,
        sucursal_id,
    )
    return int(total or 0)


async def get_pulseras_disponibles_por_sucursal(
    conn: asyncpg.Connection, sucursal_id: UUID
) -> list[PulseraResponse]:
    rows = await conn.fetch(
        """
        SELECT
            p.id,
            p.pulsera_rfid AS "pulseraRfid"
        FROM pulseras p
        WHERE p.sucursal_id = $1
        AND p.activo = TRUE
        AND NOT EXISTS (
            SELECT 1
            FROM detalles_registro dr
            WHERE dr.pulseras_id = p.id
        )
        AND NOT EXISTS (
            SELECT 1
            FROM registros r
            WHERE r.pulseras_tutor_id = p.id
        )
        ORDER BY p.pulsera_rfid
        """,
        sucursal_id,
    )

    return [PulseraResponse.model_validate(dict(r)) for r in rows]


async def esta_disponible_para_asignar(
    conn: asyncpg.Connection, pulsera_id: UUID, sucursal_id: UUID
) -> bool:
    """Comprueba y reserva la pulsera durante la transacción actual.

    Las pulseras son de un solo uso. El bloqueo de la fila evita que dos
    altas concurrentes validen la misma pulsera antes de insertar su detalle.
    """
    pulsera = await conn.fetchrow(
        """
        SELECT p.id
        FROM public.pulseras AS p
        WHERE p.id = $1
          AND p.sucursal_id = $2
          AND p.activo = TRUE
        FOR UPDATE
        """,
        pulsera_id,
        sucursal_id,
    )
    if pulsera is None:
        return False

    usada = await conn.fetchval(
        """
        SELECT EXISTS (
            SELECT 1
            FROM public.detalles_registro AS dr
            WHERE dr.pulseras_id = $1
        )
        OR EXISTS (
            SELECT 1
            FROM public.registros AS r
            WHERE r.pulseras_tutor_id = $1
        )
        """,
        pulsera_id,
    )
    return not bool(usada)


async def listar_todas(conn: asyncpg.Connection, sucursal_id: UUID) -> list[dict[str, Any]]:
    """Lista todas las pulseras de una sucursal (activas e inactivas), para administración."""
    rows = await conn.fetch(
        f"SELECT {_COLUMNS} FROM public.pulseras AS p WHERE p.sucursal_id = $1 ORDER BY p.pulsera_rfid",
        sucursal_id,
    )
    return [dict(r) for r in rows]


async def obtener(conn: asyncpg.Connection, pulsera_id: UUID) -> dict[str, Any] | None:
    row = await conn.fetchrow(
        f"SELECT {_COLUMNS} FROM public.pulseras AS p WHERE p.id = $1", pulsera_id
    )
    return dict(row) if row else None


async def crear(
    conn: asyncpg.Connection,
    sucursal_id: UUID,
    pulsera_rfid: str,
    activo: bool,
    numero_lote: str | None,
    creado_por: UUID,
) -> dict[str, Any]:
    row = await conn.fetchrow(
        """
        INSERT INTO public.pulseras (sucursal_id, pulsera_rfid, activo, numero_lote, creado_por)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING id, sucursal_id, pulsera_rfid, activo, numero_lote, creado, creado_por,
                  modificado, modificado_por
        """,
        sucursal_id,
        pulsera_rfid,
        activo,
        numero_lote,
        creado_por,
    )
    return dict(row) | {"usada": False}


async def actualizar(
    conn: asyncpg.Connection, pulsera_id: UUID, updates: dict[str, Any]
) -> dict[str, Any] | None:
    if not updates:
        return await obtener(conn, pulsera_id)
    set_parts = [f"{k} = ${i + 2}" for i, k in enumerate(updates)]
    set_parts.append("modificado = NOW()")
    sql = f"""
        UPDATE public.pulseras
        SET {', '.join(set_parts)}
        WHERE id = $1
        RETURNING id
    """
    row = await conn.fetchrow(sql, pulsera_id, *updates.values())
    return await obtener(conn, pulsera_id) if row else None


async def eliminar(conn: asyncpg.Connection, pulsera_id: UUID) -> bool:
    result = await conn.execute(
        "UPDATE public.pulseras SET activo = FALSE, modificado = NOW() "
        "WHERE id = $1 AND activo = TRUE",
        pulsera_id,
    )
    return bool(result == "UPDATE 1")
