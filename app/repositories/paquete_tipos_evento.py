from uuid import UUID

import asyncpg


async def listar_por_paquete(conn: asyncpg.Connection, paquete_id: UUID) -> list[asyncpg.Record]:
    return await conn.fetch(
        "SELECT * FROM public.paquete_tipos_evento WHERE paquete_id = $1",
        paquete_id,
    )


async def obtener(
    conn: asyncpg.Connection, paquete_id: UUID, tipo_evento_id: UUID
) -> asyncpg.Record | None:
    return await conn.fetchrow(
        """
        SELECT * FROM public.paquete_tipos_evento
        WHERE paquete_id = $1 AND tipo_evento_id = $2
        """,
        paquete_id,
        tipo_evento_id,
    )


async def agregar(
    conn: asyncpg.Connection, paquete_id: UUID, tipo_evento_id: UUID
) -> asyncpg.Record:
    return await conn.fetchrow(
        """
        INSERT INTO public.paquete_tipos_evento (paquete_id, tipo_evento_id)
        VALUES ($1, $2)
        RETURNING *
        """,
        paquete_id,
        tipo_evento_id,
    )


async def eliminar(conn: asyncpg.Connection, paquete_id: UUID, tipo_evento_id: UUID) -> str:
    return await conn.execute(
        """
        DELETE FROM public.paquete_tipos_evento
        WHERE paquete_id = $1 AND tipo_evento_id = $2
        """,
        paquete_id,
        tipo_evento_id,
    )
