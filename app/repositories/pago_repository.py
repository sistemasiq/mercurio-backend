from typing import Any
from uuid import UUID

import asyncpg

from app.schemas.pagos import PaymentItem

_INSERT = """
    INSERT INTO pagos_ordenes
        (comanda_id, metodo_pago_id, monto, notas_pago, sucursal_id, creado_por)
    VALUES ($1, $2, $3, $4, $5, $6)
    RETURNING
        id, comanda_id, metodo_pago_id, monto, notas_pago,
        sucursal_id, creado, creado_por
"""


async def crear_pagos(
    conn: asyncpg.Connection,
    comanda_id: UUID,
    sucursal_id: UUID,
    pagos: list[PaymentItem],
    usuario_id: UUID,
) -> list[dict[str, Any]]:
    resultados: list[dict[str, Any]] = []
    for pago in pagos:
        row = await conn.fetchrow(
            _INSERT,
            comanda_id,
            pago.metodo_pago_id,
            pago.monto,
            pago.notas_pago,
            sucursal_id,
            usuario_id,
        )
        resultados.append(dict(row))
    return resultados
