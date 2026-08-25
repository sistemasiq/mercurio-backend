from datetime import UTC, datetime, time, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

import asyncpg
from fastapi import HTTPException, UploadFile

from app.core.object_storage import PREFIJOS, upload_bytes, validar_y_leer
from app.core.ws_manager import manager
from app.repositories.caja_repository import registrar_movimiento_caja
from app.repositories.detalles_registro import insert_detalle_registro
from app.repositories.estancias import get_activos_by_sucursal_id
from app.repositories.ninos import nino_create
from app.repositories.pagos_comanda import pago_create
from app.repositories.productos import (
    get_precio_individual_by_id,
    get_productos_estancia_by_sucursal_id,
)
from app.repositories.registros import (
    EstadoRegistro,
    change_registro_estado,
    exists_registro_any,
    registro_create,
    registro_update_total,
)
from app.repositories.reservaciones_repository import obtener_evento_mas_cercano
from app.repositories.tutores import get_tutor_by_phone, tutor_create
from app.schemas.registros import OnboardingRequest
from app.schemas.reservaciones import EventoDelDiaOut
from app.services import lealtad_service


async def create_estancia(
    conn: asyncpg.Connection,
    data: OnboardingRequest,
    foto_ine: UploadFile,
    foto_llegada: UploadFile,
    usuario_id: UUID,
    apertura_caja_id: str,
) -> dict[str, Any]:
    async with conn.transaction():
        if data.reservacionId is not None:
            evento_dict = await obtener_evento_mas_cercano(conn, data.sucursalId)
            if evento_dict is None:
                raise HTTPException(404, "Evento no encontrado")

            # Mapeas el diccionario al modelo Pydantic
            evento = EventoDelDiaOut.model_validate(evento_dict)

            # Ahora sí, la notación de punto funcionará sin problemas
            tutor = await get_tutor_by_phone(conn, evento.telefono_cliente, data.sucursalId)

            if tutor:
                tutor_id = tutor["id"]
            else:
                if evento.apellidos_cliente:
                    nombre = f"{evento.nombre_cliente} {evento.apellidos_cliente}"
                    print(nombre)
                else:
                    nombre = evento.nombre_cliente

                tutor_id = await tutor_create(
                    conn, data.sucursalId, nombre, evento.telefono_cliente, usuario_id
                )

            # Agregar validacion para evitar que ya exista el uuid en la db
            registro_id = uuid4()
            while await exists_registro_any(conn, registro_id):
                registro_id = uuid4()

            # --- GUARDAR FOTOS FÍSICAMENTE ---
            nombre_archivo = f"{registro_id}.jpg"

            data_ine = await validar_y_leer(foto_ine)
            data_llegada = await validar_y_leer(foto_llegada)

            ruta_bd_ine = f"{PREFIJOS['identificaciones']}/{nombre_archivo}"
            ruta_bd_llegada = f"{PREFIJOS['llegadas']}/{nombre_archivo}"

            await upload_bytes(ruta_bd_ine, data_ine, "image/jpeg")
            await upload_bytes(ruta_bd_llegada, data_llegada, "image/jpeg")

            # 2. registro (Un solo INSERT limpio)
            await registro_create(
                conn,
                registro_id,
                data.sucursalId,
                tutor_id,
                data.pulseraTutorId,
                ruta_bd_ine,
                ruta_bd_llegada,
                usuario_id,
                data.nombreSegundoTutor,
                evento.id,
            )

            total = Decimal(0)

            hora_inicio_obj = (
                time.fromisoformat(evento.hora_inicio)
                if isinstance(evento.hora_inicio, str)
                else evento.hora_inicio
            )
            hora_fin_obj = (
                time.fromisoformat(evento.hora_fin)
                if isinstance(evento.hora_fin, str)
                else evento.hora_fin
            )

            fecha_base = evento.fecha_evento

            entrada = datetime.combine(fecha_base, hora_inicio_obj)
            salida_esperada = datetime.combine(fecha_base, hora_fin_obj)

            # 3. detalles
            for d in data.detalles:
                nino_id = await nino_create(
                    conn,
                    data.sucursalId,
                    d.nino.nombreCompleto,
                    d.nino.edad,
                    d.nino.notas,
                    usuario_id,
                )

                await insert_detalle_registro(
                    conn,
                    data.sucursalId,
                    registro_id,
                    nino_id,
                    d.pulseraId,
                    data.parentesco,
                    entrada,
                    salida_esperada,
                    usuario_id,
                )

            # 5. actualizar total
            await registro_update_total(conn, usuario_id, registro_id, total)

            await change_registro_estado(conn, EstadoRegistro.ACTIVO, usuario_id, registro_id)

            resultado = {
                "registroId": registro_id,
                "total": total,
                "pagado": 0,
                "estado": "A",
            }

        else:
            # 1. tutor
            tutor = await get_tutor_by_phone(conn, data.tutor.telefono, data.sucursalId)

            if tutor:
                tutor_id = tutor["id"]
            else:
                tutor_id = await tutor_create(
                    conn,
                    data.sucursalId,
                    data.tutor.nombreCompleto,
                    data.tutor.telefono,
                    usuario_id,
                )

            registro_id = uuid4()

            # --- GUARDAR FOTOS FÍSICAMENTE ---
            nombre_archivo = f"{registro_id}.jpg"

            data_ine = await validar_y_leer(foto_ine)
            data_llegada = await validar_y_leer(foto_llegada)

            ruta_bd_ine = f"{PREFIJOS['identificaciones']}/{nombre_archivo}"
            ruta_bd_llegada = f"{PREFIJOS['llegadas']}/{nombre_archivo}"

            await upload_bytes(ruta_bd_ine, data_ine, "image/jpeg")
            await upload_bytes(ruta_bd_llegada, data_llegada, "image/jpeg")

            # 2. registro (Un solo INSERT limpio)
            await registro_create(
                conn,
                registro_id,
                data.sucursalId,
                tutor_id,
                data.pulseraTutorId,
                ruta_bd_ine,
                ruta_bd_llegada,
                usuario_id,
                data.nombreSegundoTutor,
            )

            total = Decimal(0)

            # 3. detalles
            for d in data.detalles:
                nino_id = await nino_create(
                    conn,
                    data.sucursalId,
                    d.nino.nombreCompleto,
                    d.nino.edad,
                    d.nino.notas,
                    usuario_id,
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
                    data.parentesco,
                    entrada,
                    salida_esperada,
                    usuario_id,
                    d.cantidad,
                    precio,
                    d.productoId,
                )

                total += precio * d.cantidad

            # 3.5 canje de puntos de lealtad (opcional, sobre el subtotal ya calculado)
            if data.puntosARedimir > 0:
                descuento_puntos = await lealtad_service.redimir_puntos(
                    conn,
                    data.sucursalId,
                    data.tutor.telefono,
                    data.puntosARedimir,
                    None,
                    usuario_id,
                    registro_id=registro_id,
                )
                total = max(total - descuento_puntos, Decimal(0))

            # 4. pagos
            total_pagado = 0.0

            for p in data.pagos:
                await pago_create(
                    conn, data.sucursalId, registro_id, p.metodoPagoId, p.monto, usuario_id
                )
                await registrar_movimiento_caja(
                    conn,
                    apertura_caja_id=apertura_caja_id,
                    tipo_movimiento="E",
                    referencia_id=str(registro_id),
                    metodo_pago_id=str(p.metodoPagoId),
                    monto=Decimal(str(p.monto)),
                    creado_por=str(usuario_id),
                )
                total_pagado += p.monto

            # 4.5 otorgamiento de puntos de lealtad sobre lo efectivamente pagado
            if data.tutor.telefono and total_pagado > 0:
                await lealtad_service.otorgar_puntos(
                    conn,
                    data.sucursalId,
                    data.tutor.telefono,
                    Decimal(str(total_pagado)),
                    usuario_id,
                    registro_id=registro_id,
                )

            # 5. actualizar total
            await registro_update_total(conn, usuario_id, registro_id, total)

            # 6. activar si ya pagó todo
            if total_pagado >= total:
                await change_registro_estado(conn, EstadoRegistro.ACTIVO, usuario_id, registro_id)

            resultado = {
                "registroId": registro_id,
                "total": total,
                "pagado": total_pagado,
                "estado": "A" if total_pagado >= total else "P",
            }

    # Se notifica ya fuera de la transacción, para no avisar a los clientes
    # de datos que todavía podrían revertirse por un rollback.
    await manager.broadcast(
        str(data.sucursalId),
        {
            "type": "estancia_creada",
            "sucursalId": str(data.sucursalId),
            "registroId": str(registro_id),
        },
    )

    return resultado


async def get_activos_estancia_by_sucursal_id(
    conn: asyncpg.Connection, sucursal_id: UUID
) -> list[dict[str, Any]]:
    return await get_activos_by_sucursal_id(conn, sucursal_id)


async def get_productos_estancia_by_id_sucursal(
    conn: asyncpg.Connection, sucursal_id: UUID
) -> list[dict[str, Any]]:
    return await get_productos_estancia_by_sucursal_id(conn, sucursal_id)
