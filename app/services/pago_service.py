import hashlib
import json
from dataclasses import asdict
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import asyncpg

from app.exceptions import DatosInvalidos, IdempotenciaConflictoError
from app.models.comanda import Comanda
from app.repositories import (
    comanda_repository,
    folio_repository,
    metodos_pago_repository,
    pago_repository,
)
from app.repositories.caja_repository import registrar_cambio_caja, registrar_movimiento_caja
from app.schemas.comanda import ComandaCreate, EstadoComanda
from app.schemas.pagos import (
    DetalleOrdenOut,
    EstadisticasOut,
    HistorialOut,
    PagoCompletoRequest,
    PaymentOut,
    PaymentRequest,
)
from app.services import inventario_service, lealtad_service
from app.services.validaciones_pago import validar_cambio


def _hash_payload(body: PagoCompletoRequest) -> str:
    """Hash estable del payload para detectar reintentos con la misma
    Idempotency-Key pero datos distintos (QA #20)."""
    payload_json = json.dumps(body.model_dump(mode="json"), sort_keys=True)
    return hashlib.sha256(payload_json.encode("utf-8")).hexdigest()


async def procesar_pagos(
    conn: asyncpg.Connection,
    body: PaymentRequest,
    usuario_id: UUID,
) -> list[PaymentOut]:
    total_pagos: Decimal = sum((p.monto for p in body.pagos), Decimal(0))

    if total_pagos != body.total_esperado:
        raise DatosInvalidos(
            f"El total de los pagos ({total_pagos}) no coincide "
            f"con el total esperado ({body.total_esperado})."
        )

    rows = await pago_repository.crear_pagos(
        conn,
        comanda_id=body.comanda_id,
        sucursal_id=body.sucursal_id,
        pagos=body.pagos,
        usuario_id=usuario_id,
    )

    return [PaymentOut.model_validate(r) for r in rows]


async def completar_pago(
    conn: asyncpg.Connection,
    body: PagoCompletoRequest,
    usuario_id: UUID,
    sucursal_id: UUID,
    apertura_caja_id: str,
    idempotency_key: str | None = None,
) -> Comanda:
    """Crea la comanda, registra los pagos, el movimiento de caja de cada uno
    y, si hubo cambio, su propio movimiento
    (multimodal: una comanda puede pagarse con varios métodos) en una única
    transacción. Si falla cualquiera de los dos, nada se persiste (rollback
    automático). Después del commit, expande los detalles de combos y
    notifica a cocina vía WebSocket.

    Si viene `idempotency_key` (header Idempotency-Key, QA #20): si la clave
    ya existe con el mismo hash de payload, devuelve la comanda original sin
    volver a cobrar ni descontar inventario; si existe con un hash distinto,
    lanza 409 IDEMPOTENCIA_CONFLICTO. Sin header, el comportamiento es idéntico
    al previo.
    """
    from app.core.ws_manager import manager
    from app.services.comanda_service import expandir_detalles_comanda

    hash_payload = _hash_payload(body) if idempotency_key else None

    if idempotency_key:
        existente = await pago_repository.obtener_idempotencia(conn, idempotency_key)
        if existente:
            if existente["hash_payload"] != hash_payload:
                raise IdempotenciaConflictoError()
            comanda_original = await comanda_repository.get_comanda_por_id(
                conn, str(existente["comanda_id"])
            )
            if comanda_original is not None:
                comanda_original.detalles = await expandir_detalles_comanda(
                    conn, comanda_original.detalles
                )
                return comanda_original

    total_pagos: Decimal = sum((p.monto for p in body.pagos), Decimal(0))
    if total_pagos < body.total_final:
        raise DatosInvalidos(
            f"El total de los pagos ({total_pagos}) es menor "
            f"al total de la comanda ({body.total_final})."
        )

    ids_efectivo = await metodos_pago_repository.obtener_ids_por_tipo(conn, "E")
    cambio = body.cambio.quantize(Decimal("0.01"))
    if cambio > total_pagos - body.total_final:
        raise DatosInvalidos(
            f"El cambio declarado ({cambio}) es mayor al excedente pagado "
            f"({total_pagos - body.total_final})."
        )
    validar_cambio(
        [(p.metodo_pago_id, p.monto) for p in body.pagos],
        cambio,
        ids_efectivo,
    )

    async with conn.transaction():
        # Folio de ticket secuencial por sucursal (QA #21): el backend asigna
        # ticket_numero de forma atómica dentro de esta transacción.
        # body.ticket_numero (lo que mande el front, si manda algo) queda solo
        # como fallback si por algún motivo siguiente_folio no devuelve nada;
        # como último recurso, un folio temporal para no bloquear el cobro.
        ticket_numero = (
            await folio_repository.siguiente_folio(conn, sucursal_id)
            or body.ticket_numero
            or f"T{uuid4().hex[:7].upper()}"
        )

        comanda_in = ComandaCreate(
            ticket_numero=ticket_numero,
            total_final=body.total_final,
            estado_actual=EstadoComanda.PENDIENTE,
            detalles_comanda=body.detalles_comanda,
            notas_generales=body.notas_generales,
            sucursal_id=sucursal_id,
            nombre_cliente=body.nombre_cliente,
            mesa=body.mesa,
        )

        comanda = await comanda_repository.crear_comanda_con_detalles(
            conn,
            comanda_in,
            None,
            str(usuario_id),
        )
        await inventario_service.descontar_por_venta(
            conn,
            str(sucursal_id),
            body.detalles_comanda,
            comanda.id,
            usuario_id,
        )
        await pago_repository.crear_pagos(
            conn,
            comanda_id=UUID(comanda.id),
            sucursal_id=sucursal_id,
            pagos=body.pagos,
            usuario_id=usuario_id,
        )
        if idempotency_key and hash_payload:
            await pago_repository.registrar_idempotencia(
                conn,
                clave=idempotency_key,
                sucursal_id=sucursal_id,
                usuario_id=usuario_id,
                hash_payload=hash_payload,
                comanda_id=UUID(comanda.id),
            )
        for pago in body.pagos:
            await registrar_movimiento_caja(
                conn,
                apertura_caja_id=apertura_caja_id,
                tipo_movimiento="O",
                referencia_id=comanda.id,
                metodo_pago_id=str(pago.metodo_pago_id),
                monto=pago.monto,
                creado_por=str(usuario_id),
            )
        if cambio > 0:
            await registrar_cambio_caja(
                conn,
                apertura_caja_id=apertura_caja_id,
                referencia_id=comanda.id,
                monto=cambio,
                creado_por=str(usuario_id),
            )
        if body.puntos_a_redimir > 0:
            # celular_cliente es obligatorio en este caso (validado en el schema).
            descuento = await lealtad_service.redimir_puntos(
                conn,
                sucursal_id,
                body.celular_cliente,  # type: ignore[arg-type]
                body.puntos_a_redimir,
                UUID(comanda.id),
                usuario_id,
            )
            subtotal_bruto: Decimal = sum((d.subtotal for d in body.detalles_comanda), Decimal(0))
            esperado = subtotal_bruto - descuento
            if body.total_final != esperado:
                raise DatosInvalidos(
                    f"El total final ({body.total_final}) no coincide con el subtotal "
                    f"menos el descuento por puntos canjeados ({esperado})."
                )
        if body.celular_cliente:
            await lealtad_service.otorgar_puntos(
                conn,
                sucursal_id,
                body.celular_cliente,
                body.total_final,
                usuario_id,
                comanda_id=UUID(comanda.id),
            )

    comanda.detalles = await expandir_detalles_comanda(conn, comanda.detalles)

    await manager.broadcast(
        str(sucursal_id),
        {"type": "comanda_creada", "comanda": asdict(comanda)},
    )

    return comanda


def _calcular_desde(filtro: str) -> datetime:
    ahora = datetime.now()
    if filtro == "hoy":
        return ahora.replace(hour=0, minute=0, second=0, microsecond=0)
    if filtro == "semana":
        inicio_semana = ahora - timedelta(days=ahora.weekday())
        return inicio_semana.replace(hour=0, minute=0, second=0, microsecond=0)
    return ahora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


async def obtener_historial(
    conn: asyncpg.Connection,
    sucursal_id: UUID,
    filtro: str = "hoy",
    estado: str = "todos",
    fecha_inicio: str | None = None,
    fecha_fin: str | None = None,
) -> list[HistorialOut]:
    desde = _calcular_desde(filtro)
    hasta = None
    if fecha_inicio:
        desde = datetime.fromisoformat(fecha_inicio)
    if fecha_fin:
        hasta = datetime.fromisoformat(fecha_fin).replace(hour=23, minute=59, second=59)
    rows = await pago_repository.historial(conn, sucursal_id, desde, estado, hasta)
    return [HistorialOut.model_validate(r) for r in rows]


async def obtener_detalle(
    conn: asyncpg.Connection,
    tipo_origen: str,
    referencia_id: UUID,
) -> DetalleOrdenOut | None:
    data = await pago_repository.detalle_por_referencia(conn, tipo_origen, referencia_id)
    if data is None:
        return None
    return DetalleOrdenOut.model_validate(data)


async def obtener_estadisticas(
    conn: asyncpg.Connection,
    sucursal_id: UUID,
    filtro: str = "hoy",
    fecha_inicio: str | None = None,
    fecha_fin: str | None = None,
) -> EstadisticasOut:
    desde = _calcular_desde(filtro)
    hasta = None
    if fecha_inicio:
        desde = datetime.fromisoformat(fecha_inicio)
    if fecha_fin:
        hasta = datetime.fromisoformat(fecha_fin).replace(hour=23, minute=59, second=59)
    data = await pago_repository.estadisticas(conn, sucursal_id, desde, hasta)
    total_ventas = float(data["total_ventas"])
    total_ordenes = int(data["total_ordenes"])
    ticket_promedio = total_ventas / total_ordenes if total_ordenes > 0 else 0.0
    return EstadisticasOut(
        total_ventas=total_ventas,
        total_ordenes=total_ordenes,
        ticket_promedio=ticket_promedio,
    )
