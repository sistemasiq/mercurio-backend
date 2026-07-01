import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

import asyncpg
from fastapi import HTTPException, UploadFile

from app.core.storage import IDENTIFICACIONES_DIR, LLEGADAS_DIR
from app.repositories.detalles_registro import insert_detalle_registro
from app.repositories.estancias import get_activos_by_sucursal_id
from app.repositories.ninos import nino_create
from app.repositories.pagos import pago_create
from app.repositories.productos import (
    get_precio_individual_by_id,
    get_productos_estancia_by_sucursal_id,
)
from app.repositories.registros import (
    EstadoRegistro,
    change_registro_estado,
    registro_create,
    registro_update_total,
)
from app.repositories.tutores import get_tutor_by_phone, tutor_create
from app.schemas.registros import OnboardingRequest


async def create_estancia(
    conn: asyncpg.Connection,
    data: OnboardingRequest,
    foto_ine: UploadFile,
    foto_llegada: UploadFile,
    usuario_id: UUID,
) -> dict[str, Any]:
    async with conn.transaction():
        # 1. tutor
        tutor = await get_tutor_by_phone(conn, data.tutor.telefono, data.sucursalId)

        if tutor:
            tutor_id = tutor["id"]
        else:
            tutor_id = await tutor_create(
                conn, data.sucursalId, data.tutor.nombreCompleto, data.tutor.telefono, usuario_id
            )

        registro_id = uuid4()

        # --- GUARDAR FOTOS FÍSICAMENTE ---
        nombre_archivo = f"{registro_id}.jpg"
        ruta_fisica_ine = IDENTIFICACIONES_DIR / nombre_archivo
        ruta_fisica_llegada = LLEGADAS_DIR / nombre_archivo

        await asyncio.to_thread(ruta_fisica_ine.write_bytes, await foto_ine.read())
        await asyncio.to_thread(ruta_fisica_llegada.write_bytes, await foto_llegada.read())

        # Rutas relativas para guardar en BD
        ruta_bd_ine = f"uploads/identificaciones/{nombre_archivo}"
        ruta_bd_llegada = f"uploads/llegadas/{nombre_archivo}"

        # 2. registro (Un solo INSERT limpio)
        await registro_create(
            conn, registro_id, data.sucursalId, tutor_id, ruta_bd_ine, ruta_bd_llegada, usuario_id
        )

        total = Decimal(0)

        # 3. detalles
        for d in data.detalles:
            nino_id = await nino_create(
                conn, data.sucursalId, d.nino.nombreCompleto, d.nino.edad, d.nino.notas, usuario_id
            )

            precio = await get_precio_individual_by_id(conn, d.productoId)

            if precio is None:
                raise HTTPException(400, "Producto inválido")

            entrada = datetime.now(UTC)

            salida_esperada = entrada + timedelta(hours=d.cantidad)

            await insert_detalle_registro(
                conn,
                data.sucursalId,
                registro_id,
                nino_id,
                d.pulseraId,
                d.productoId,
                d.cantidad,
                precio,
                data.parentesco,
                entrada,
                salida_esperada,
                usuario_id,
            )

            total += precio * d.cantidad

        # 4. pagos
        total_pagado = 0.0

        for p in data.pagos:
            await pago_create(
                conn, data.sucursalId, registro_id, p.metodoPagoId, p.monto, usuario_id
            )
            total_pagado += p.monto

        # 5. actualizar total
        await registro_update_total(conn, registro_id, total)

        # 6. activar si ya pagó todo
        if total_pagado >= total:
            await change_registro_estado(conn, EstadoRegistro.ACTIVO, registro_id)

        return {
            "registroId": registro_id,
            "total": total,
            "pagado": total_pagado,
            "estado": "A" if total_pagado >= total else "P",
        }


async def get_activos_estancia_by_sucursal_id(
    conn: asyncpg.Connection, sucursal_id: UUID
) -> list[dict[str, Any]]:
    return await get_activos_by_sucursal_id(conn, sucursal_id)


async def get_productos_estancia_by_id_sucursal(
    conn: asyncpg.Connection, sucursal_id: UUID
) -> list[dict[str, Any]]:
    return await get_productos_estancia_by_sucursal_id(conn, sucursal_id)
