from decimal import Decimal
from uuid import UUID

import asyncpg
from fastapi import HTTPException

from app.repositories.caja_repository import registrar_movimiento_caja
from app.repositories.pagos import pago_create
from app.repositories.registros import exists_registro
from app.schemas.pagos import PagoIn


async def pago_create_service(
    conn: asyncpg.Connection,
    data: list[PagoIn],
    sucursal_id: UUID,
    registro_id: UUID,
    usuario_id: UUID,
    apertura_caja_id: str,
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
            await registrar_movimiento_caja(
                conn,
                id_apertura_caja=apertura_caja_id,
                tipo_movimiento="E",
                id_referencia=str(registro_id),
                id_metodo_pago=str(pago.metodoPagoId),
                monto=Decimal(str(pago.monto)),
                creado_por=str(usuario_id),
            )
    else:
        raise HTTPException(404, "Registro no encontrado")
