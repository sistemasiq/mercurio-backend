from uuid import UUID

import asyncpg
from fastapi import HTTPException

from app.repositories.pagos_comanda import pago_create
from app.repositories.registros import exists_registro
from app.schemas.pagos import PagoIn


async def pago_create_service(
    conn: asyncpg.Connection,
    data: list[PagoIn],
    sucursal_id: UUID,
    registro_id: UUID,
    usuario_id: UUID,
) -> None:
    registro = await exists_registro(conn, registro_id)

    if registro:
        for pago in data:
            await pago_create(
                conn,
                sucursal_id,
                registro_id,
                pago.metodoPagoId,
                pago.monto,
                usuario_id,
            )
    else:
        raise HTTPException(404, "Registro no encontrado")
