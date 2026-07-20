from datetime import UTC, datetime
from math import ceil
from typing import Any
from uuid import UUID

import asyncpg
from fastapi import HTTPException

from app.core.ws_manager import manager
from app.repositories.cargos_extra_estancia import make_extra_charge
from app.repositories.detalles_registro import (
    count_detalles_registro_abiertos,
    get_detalle_registro_by_id,
    put_hora_salida_by_id,
)
from app.repositories.registros import EstadoRegistro, get_guardian_bracelet_by_detalles_registro_id,change_registro_estado, registro_add_total

EXTRA_GRACE_MINUTES = 5


async def create_chekout(
    conn: asyncpg.Connection, detalle_id: UUID, pulsera_tutor_id: UUID, usuario_id: UUID
) -> dict[str, Any]:
    async with conn.transaction():
        now = datetime.now(UTC)

        detalle = await get_detalle_registro_by_id(conn, detalle_id)

        if not detalle:
            raise HTTPException(404, "Detalle no encontrado")

        if detalle["salida"] is not None:
            raise HTTPException(400, "El niño ya realizó checkout")

        salida_esperada = detalle["salida_esperada"]

        if salida_esperada is None:
            raise HTTPException(400, "Detalle sin salida esperada")
        
        pulsera_tutor_id_db = await get_guardian_bracelet_by_detalles_registro_id(conn,detalle["registros_id"])

        if pulsera_tutor_id_db is None or str(pulsera_tutor_id) != str(pulsera_tutor_id_db):
            raise HTTPException(403,"La pulsera presentada no corresponde al tutor autorizado")

        minutos_extra = (now - salida_esperada).total_seconds() / 60

        extra_horas = 0

        if minutos_extra > EXTRA_GRACE_MINUTES:
            extra_horas = ceil((minutos_extra - EXTRA_GRACE_MINUTES) / 60)

        total_extra = detalle["precio"] * extra_horas

        await put_hora_salida_by_id(conn, usuario_id, detalle_id)

        if extra_horas > 0:
            await make_extra_charge(
                conn,
                detalle["sucursal_id"],
                detalle["registros_id"],
                detalle_id,
                extra_horas,
                detalle["precio"],
                total_extra,
                usuario_id,
            )
            await registro_add_total(conn, total_extra, usuario_id, detalle["registros_id"])

        abiertos = await count_detalles_registro_abiertos(conn, detalle["registros_id"])

        if abiertos == 0:
            await change_registro_estado(conn, EstadoRegistro.CERRADO, usuario_id, detalle["registros_id"])

        resultado = {
            "detalleId": str(detalle_id),
            "registroId": str(detalle["registros_id"]),
            "horasExtra": extra_horas,
            "totalExtra": float(total_extra),
            "ninosRestantes": abiertos,
        }

    # Se notifica ya fuera de la transacción, para no avisar a los clientes de datos que todavía podrían revertirse por un rollback.
    await manager.broadcast(
        str(detalle["sucursal_id"]),
        {
            "type": "estancia_checkout",
            "sucursalId": str(detalle["sucursal_id"]),
            "detalleId": str(detalle_id),
            "registroId": str(detalle["registros_id"]),
        },
    )

    return resultado