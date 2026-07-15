from dataclasses import asdict
from decimal import Decimal
from uuid import UUID

import asyncpg

from app.exceptions import DatosInvalidos
from app.models.comanda import Comanda
from app.repositories import comanda_repository, pago_repository
from app.schemas.comanda import ComandaCreate, EstadoComanda
from app.schemas.pagos import PaymentOut, PaymentRequest, PagoCompletoRequest


async def procesar_pagos(
    conn: asyncpg.Connection,
    body: PaymentRequest,
    usuario_id: UUID,
) -> list[PaymentOut]:
    total_pagos: Decimal = sum(p.monto for p in body.pagos)

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
) -> Comanda:
    """Crea la comanda y registra los pagos en una única transacción.

    Si falla cualquiera de los dos, nada se persiste (rollback automático).
    Después del commit, expande los detalles de combos y notifica a cocina
    vía WebSocket.
    """
    from app.core.ws_manager import manager
    from app.services.comanda_service import expandir_detalles_comanda

    total_pagos: Decimal = sum(p.monto for p in body.pagos)
    if total_pagos != body.total_final:
        raise DatosInvalidos(
            f"El total de los pagos ({total_pagos}) no coincide "
            f"con el total de la comanda ({body.total_final})."
        )

    comanda_in = ComandaCreate(
        ticket_numero=body.ticket_numero,
        total_final=body.total_final,
        estado_actual=EstadoComanda.PENDIENTE,
        detalles_comanda=body.detalles_comanda,
        notas_generales=body.notas_generales,
        sucursal_id=sucursal_id,
    )

    async with conn.transaction():
        comanda = await comanda_repository.crear_comanda_con_detalles(
            conn, comanda_in, None, str(usuario_id),
        )
        await pago_repository.crear_pagos(
            conn,
            comanda_id=UUID(comanda.id),
            sucursal_id=sucursal_id,
            pagos=body.pagos,
            usuario_id=usuario_id,
        )

    comanda.detalles = await expandir_detalles_comanda(conn, comanda.detalles)

    await manager.broadcast(
        sucursal_id,
        {"type": "comanda_creada", "comanda": asdict(comanda)},
    )

    return comanda
