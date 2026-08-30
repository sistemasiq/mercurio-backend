from datetime import UTC, datetime, time, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4
import json
import asyncpg
from fastapi import HTTPException, UploadFile

from app.core.object_storage import PREFIJOS, upload_bytes, validar_y_leer
from app.core.ws_manager import manager
from app.repositories.caja_repository import registrar_movimiento_caja
from app.repositories.detalles_registro import insert_detalle_registro
from app.repositories.estancias import get_activos_by_sucursal_id
from app.repositories.fotos import foto_create, TipoFoto
from app.repositories.ninos import nino_create
from app.repositories.pagos_comanda import pago_create
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
from app.repositories.reservaciones_repository import obtener_evento_mas_cercano
from app.repositories.producto_repository import get_producto_estancia_by_branch_id
from app.repositories.productos import get_precio_pulsera_by_reserva_id
from app.repositories.tutores import get_tutor_by_phone, tutor_create
from app.schemas.registros import OnboardingRequest
from app.schemas.reservaciones import EventoDelDiaOut


async def create_estancia(
    conn: asyncpg.Connection,
    data: OnboardingRequest,
    foto_ine: UploadFile,
    foto_llegadas: list[UploadFile],
    usuario_id: UUID,
    apertura_caja_id: str,
) -> dict[str, Any]:
    async with conn.transaction():

        if data.reservacionId is not None:
            evento_dict = await obtener_evento_mas_cercano(conn, data.sucursalId)
            if evento_dict is None:
                raise HTTPException(404, "Evento no encontrado")

            # Mapeo de diccionario a modelo Pydantic
            evento = EventoDelDiaOut.model_validate(evento_dict)

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
            
            registro_id = uuid4()

            # --- GUARDAR FOTOS FÍSICAMENTE ---
            nombre_archivo = f"{registro_id}.jpg"

            data_ine = await validar_y_leer(foto_ine)
            data_llegadas = [await validar_y_leer(foto) for foto in foto_llegadas]

            ruta_bd_ine = f"{PREFIJOS['identificaciones']}/{nombre_archivo}"

            await upload_bytes(ruta_bd_ine, data_ine, "image/jpeg")

            # 2. registro (Un solo INSERT limpio)
            await registro_create(
                conn, registro_id, data.sucursalId, tutor_id, usuario_id, data.nombreSegundoTutor,evento.id
            )

            # 3. fotos
            await foto_create(conn, registro_id, TipoFoto.INE, ruta_bd_ine, usuario_id)
            for data_llegada in data_llegadas:
                foto_id = uuid4()
                ruta_llegada = f"uploads/llegadas/{foto_id}.jpg"
                await upload_bytes(ruta_llegada, data_llegada, "image/jpeg")
                await foto_create(conn, registro_id, TipoFoto.LLEGADA, ruta_llegada, usuario_id, foto_id)

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

            # Calcular cantidad de horas segun el evento
            cantidad_horas = int((salida_esperada - entrada).total_seconds() / 3600)

            # 4. detalles

            precio = await get_precio_pulsera_by_reserva_id(conn, data.reservacionId)

            for d in data.detalles:
                nino_id = await nino_create(
                    conn, data.sucursalId, d.nino.nombreCompleto, d.nino.edad, d.nino.notas, usuario_id
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
                    cantidad_horas,
                    precio,
                    d.productoId,
                )

                total += precio * cantidad_horas

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
                    conn, data.sucursalId, data.tutor.nombreCompleto, data.tutor.telefono, usuario_id
                )

            registro_id = uuid4()

            # --- GUARDAR FOTOS FÍSICAMENTE ---
            nombre_archivo = f"{registro_id}.jpg"

            data_ine = await validar_y_leer(foto_ine)
            data_llegadas = [await validar_y_leer(foto) for foto in foto_llegadas]

            ruta_bd_ine = f"{PREFIJOS['identificaciones']}/{nombre_archivo}"

            await upload_bytes(ruta_bd_ine, data_ine, "image/jpeg")

            # 2. registro (Un solo INSERT limpio)
            await registro_create(
                conn, registro_id, data.sucursalId, tutor_id, usuario_id, data.nombreSegundoTutor
            )

            total = Decimal(0)

            # 3. fotos
            await foto_create(conn, registro_id, TipoFoto.INE, ruta_bd_ine, usuario_id)
            for data_llegada in data_llegadas:
                foto_id = uuid4()
                ruta_llegada = f"uploads/llegadas/{foto_id}.jpg"
                await upload_bytes(ruta_llegada, data_llegada, "image/jpeg")
                await foto_create(conn, registro_id, TipoFoto.LLEGADA, ruta_llegada, usuario_id, foto_id)

            # 4. detalles
            producto_estancia = await get_producto_estancia_by_branch_id(conn, data.sucursalId)

            if producto_estancia is None:
                raise HTTPException(400, "Producto inválido")

            # Lectura y deserialización del Record
            raw_config = producto_estancia["config_estancia"]

            precios = []
            if isinstance(raw_config, str):
                try:
                    precios = json.loads(raw_config)
                except Exception:
                    import ast
                    try:
                        precios = ast.literal_eval(raw_config)
                    except Exception:
                        precios = []
            elif isinstance(raw_config, list):
                precios = raw_config


            for d in data.detalles:
                nino_id = await nino_create(
                    conn, data.sucursalId, d.nino.nombreCompleto, d.nino.edad, d.nino.notas, usuario_id
                )

                entrada = datetime.now(UTC)
                salida_esperada = entrada + timedelta(hours=d.cantidad)

                # Buscar el precio correspondiente en los tramos
                precio = None
                cantidad_horas = float(d.cantidad)

                for config in precios:
                    min_h = float(config["min_horas"])
                    max_h = float(config["max_horas"])
                    p_val = Decimal(str(config["precio"]))

                    if min_h <= cantidad_horas <= max_h:
                        precio = p_val
                        break
                
                if precio is None:
                    raise HTTPException(
                        400, 
                        f"No se encontró un precio válido para la duración especificada ({d.cantidad} hrs)"
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
                    d.cantidad,
                    precio,
                    d.productoId,
                )

                # Si el precio del tramo ya es la tarifa plana del rango
                total += precio * d.cantidad

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

            # 5. actualizar total
            await registro_update_total(conn, usuario_id, registro_id, total)

            # 6. activar si ya pagó todo
            print("Total pagado: ", total_pagado, " total: ", total)
            if total_pagado >= total:
                await change_registro_estado(conn, EstadoRegistro.ACTIVO,usuario_id, registro_id)
            else:
                raise HTTPException(400, "No se pudo activar el registro porque no se pagó el total")

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

