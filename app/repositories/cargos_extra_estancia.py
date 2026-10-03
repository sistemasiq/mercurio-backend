from uuid import UUID

import asyncpg


async def make_extra_charge(
    conn: asyncpg.Connection,
    sucursal_id: UUID,
    registros_id: UUID,
    detalle_id: UUID,
    extra_horas: int,
    precio: float,
    total_extra: float,
    usuario_id: UUID,
) -> str:
    result = await conn.execute(
        """
                   INSERT INTO cargos_extra_estancia (
                       sucursal_id,
                       registros_id,
                       detalles_registro_id,
                       cantidad,
                       precio,
                       total,
                       creado_por
                   )
                   VALUES ($1,$2,$3,$4,$5,$6,$7)
               """,
        sucursal_id,
        registros_id,
        detalle_id,
        extra_horas,
        precio,
        total_extra,
        usuario_id,
    )
    return str(result)
