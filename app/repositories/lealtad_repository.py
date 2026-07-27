from typing import Any
from uuid import UUID

import asyncpg

_SELECT = """
    SELECT sucursal_id, porcentaje_retorno, dias_caducidad, valor_punto, activo,
           creado, creado_por, modificado, modificado_por
    FROM configuracion_lealtad
"""


async def obtener_configuracion(
    conn: asyncpg.Connection, sucursal_id: UUID
) -> dict[str, Any] | None:
    row = await conn.fetchrow(_SELECT + " WHERE sucursal_id = $1", sucursal_id)
    return dict(row) if row else None


async def upsert_configuracion(
    conn: asyncpg.Connection,
    sucursal_id: UUID,
    porcentaje_retorno: float,
    dias_caducidad: int,
    valor_punto: float,
    activo: bool,
    usuario_id: UUID,
) -> dict[str, Any]:
    row = await conn.fetchrow(
        """
        INSERT INTO configuracion_lealtad
            (sucursal_id, porcentaje_retorno, dias_caducidad, valor_punto,
             activo, creado_por, modificado_por)
        VALUES ($1, $2, $3, $4, $5, $6, $6)
        ON CONFLICT (sucursal_id) DO UPDATE SET
            porcentaje_retorno = EXCLUDED.porcentaje_retorno,
            dias_caducidad = EXCLUDED.dias_caducidad,
            valor_punto = EXCLUDED.valor_punto,
            activo = EXCLUDED.activo,
            modificado = NOW(),
            modificado_por = EXCLUDED.modificado_por
        RETURNING sucursal_id, porcentaje_retorno, dias_caducidad, valor_punto, activo,
                  creado, creado_por, modificado, modificado_por
        """,
        sucursal_id,
        porcentaje_retorno,
        dias_caducidad,
        valor_punto,
        activo,
        usuario_id,
    )
    return dict(row)
