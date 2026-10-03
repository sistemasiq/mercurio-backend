from datetime import date
from uuid import UUID

import asyncpg

from app.exceptions import DatosInvalidos, NoEncontrado
from app.repositories import (
    registros,
    reservacion_extras_repository,
    reservacion_productos_repository,
    reservaciones_repository,
)
from app.schemas.pagos_reservacion import PagosReservacionCompletarRequest
from app.schemas.reservacion_extras import ReservacionExtrasOut
from app.schemas.reservacion_productos import ReservacionProductosOut
from app.schemas.reservaciones import (
    EventoDelDiaOut,
    ReservacionesCrear,
    ReservacionesOut,
    ReservacionesUpdate,
)
from app.schemas.reservaciones_completa import (
    ReservacionCompletaRequest,
    ReservacionCompletaResponse,
)


async def listar(
    conn: asyncpg.Connection,
    scope: str | None = None,
    desde: date | None = None,
    hasta: date | None = None,
) -> list[ReservacionesOut]:
    rows = await reservaciones_repository.listar(conn, scope, desde, hasta)
    return [ReservacionesOut.model_validate(r) for r in rows]


async def obtener_evento_cercano(
    conn: asyncpg.Connection, sucursal_id: UUID
) -> EventoDelDiaOut | None:
    row = await reservaciones_repository.obtener_evento_mas_cercano(conn, sucursal_id)
    if not row:
        return None

    registro_existente = await registros.exists_registro_by_reservacion_id(conn, row["id"])
    if registro_existente:
        return None

    return EventoDelDiaOut.model_validate(row)


async def obtener(conn: asyncpg.Connection, reservacion_id: UUID) -> ReservacionesOut:
    row = await reservaciones_repository.obtener(conn, reservacion_id)
    if not row or not row["activo"]:
        raise NoEncontrado("Reservación")
    return ReservacionesOut.model_validate(row)


async def crear(
    conn: asyncpg.Connection, body: ReservacionesCrear, user_id: str
) -> ReservacionesOut:
    # RN-CIE-001: si la reservación trae un anticipo (dinero que se cobra en el momento),
    # exige turno abierto igual que cualquier otra venta — de lo contrario el paso
    # siguiente (POST /pagos-reservacion) rechaza el cobro y la reservación queda
    # "confirmada" con un anticipo que nunca se registró como dinero real.
    # Agendar sin cobrar nada (anticipo=0) no requiere turno.
    if body.anticipo > 0:
        from app.services.turnos_caja_service import verificar_turno_abierto

        await verificar_turno_abierto(conn, user_id)

    data = body.model_dump()
    data["folio"] = await reservaciones_repository.siguiente_folio(conn)
    row = await reservaciones_repository.crear(conn, data)
    return ReservacionesOut.model_validate(row)


async def actualizar(
    conn: asyncpg.Connection, reservacion_id: UUID, body: ReservacionesUpdate
) -> ReservacionesOut:
    actual = await obtener(conn, reservacion_id)
    updates = body.model_dump(exclude_unset=True)
    hora_inicio = updates.get("hora_inicio", actual.hora_inicio)
    hora_fin = updates.get("hora_fin", actual.hora_fin)
    if hora_fin <= hora_inicio:
        raise DatosInvalidos("hora_fin debe ser mayor a hora_inicio")
    row = await reservaciones_repository.actualizar(conn, reservacion_id, updates)
    if not row:
        raise NoEncontrado("Reservación")
    return ReservacionesOut.model_validate(row)


async def eliminar(conn: asyncpg.Connection, reservacion_id: UUID) -> None:
    await obtener(conn, reservacion_id)
    await reservaciones_repository.eliminar(conn, reservacion_id)


async def crear_completa(
    conn: asyncpg.Connection,
    body: ReservacionCompletaRequest,
    usuario_id: UUID,
    apertura_caja_id: str,
) -> ReservacionCompletaResponse:
    """Alta atómica de la reservación con sus extras, productos y pagos (QA
    #10): si algo falla, nada se persiste. Reusa crear() (folio + validación
    de turno) y pagos_reservacion.completar() (cambio + lealtad) dentro de la
    misma transacción -- los extras y productos se insertan por repository
    directo, igual que hacían los servicios de esos recursos, pero sin la
    validación de scope de TokenData que ahí no aplica (el usuario ya quedó
    autorizado a nivel de endpoint)."""
    # Import diferido: evita el ciclo de imports de pagos_reservacion <->
    # reservaciones que ya existe entre sus services.
    from app.services import pagos_reservacion as pagos_reservacion_svc

    async with conn.transaction():
        reservacion_out = await crear(conn, body.reservacion, str(usuario_id))

        extras_out: list[ReservacionExtrasOut] = []
        for item in body.extras:
            fila = await reservacion_extras_repository.crear(
                conn,
                reservacion_id=reservacion_out.id,
                extra_id=item.extra_id,
                cantidad=item.cantidad,
                precio_unitario=item.precio_unitario,
            )
            extras_out.append(ReservacionExtrasOut.model_validate(fila))

        productos_out: list[ReservacionProductosOut] = []
        for producto_item in body.productos:
            fila = await reservacion_productos_repository.crear(
                conn,
                reservacion_id=reservacion_out.id,
                producto_id=producto_item.producto_id,
                cantidad=producto_item.cantidad,
                precio_unitario=producto_item.precio_unitario,
                notas=producto_item.notas,
                creado_por=usuario_id,
            )
            productos_out.append(ReservacionProductosOut.model_validate(fila))

        pagos_out = []
        cambio = body.cambio
        advertencia_efectivo: str | None = None
        if body.pagos:
            resultado_pagos = await pagos_reservacion_svc.completar(
                conn,
                PagosReservacionCompletarRequest(
                    reservacion_id=reservacion_out.id,
                    pagos=body.pagos,
                    cambio=body.cambio,
                ),
                usuario_id,
                apertura_caja_id,
            )
            pagos_out = resultado_pagos.pagos
            cambio = resultado_pagos.cambio

    return ReservacionCompletaResponse(
        reservacion=reservacion_out,
        extras=extras_out,
        productos=productos_out,
        pagos=pagos_out,
        cambio=cambio,
        advertencia_efectivo=advertencia_efectivo,
    )
