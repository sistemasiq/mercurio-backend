from datetime import UTC, date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

import asyncpg

from app.core.roles import ROL_SISTEMA
from app.exceptions import DatosInvalidos, NoEncontrado, SaldoInsuficienteError
from app.repositories import lealtad_repository
from app.schemas.auth import TokenData
from app.schemas.lealtad import (
    ConfiguracionLealtadBase,
    ConfiguracionLealtadOut,
    MovimientoPuntoOut,
    ReporteLealtadOut,
    SaldoPuntosOut,
)


def resolver_sucursal(current_user: TokenData, sucursal_id: UUID | None) -> UUID:
    """AdministradorSistema ve todas las sucursales, así que debe indicar
    explícitamente cuál configurar/consultar. El resto usa su sucursal activa."""
    if current_user.role == ROL_SISTEMA:
        if sucursal_id is None:
            raise DatosInvalidos("Debes indicar sucursal_id (AdministradorSistema ve todas).")
        return sucursal_id
    if current_user.branch_id is None:
        raise DatosInvalidos("La sesión no tiene una sucursal activa.")
    return current_user.branch_id


async def obtener_configuracion(
    conn: asyncpg.Connection, current_user: TokenData, sucursal_id: UUID | None
) -> ConfiguracionLealtadOut:
    scope = resolver_sucursal(current_user, sucursal_id)
    row = await lealtad_repository.obtener_configuracion(conn, scope)
    if not row:
        raise NoEncontrado("Configuración de lealtad")
    return ConfiguracionLealtadOut.model_validate(row)


async def actualizar_configuracion(
    conn: asyncpg.Connection,
    current_user: TokenData,
    sucursal_id: UUID | None,
    body: ConfiguracionLealtadBase,
) -> ConfiguracionLealtadOut:
    scope = resolver_sucursal(current_user, sucursal_id)
    row = await lealtad_repository.upsert_configuracion(
        conn,
        scope,
        porcentaje_retorno=body.porcentaje_retorno,
        dias_caducidad=body.dias_caducidad,
        valor_punto=body.valor_punto,
        activo=body.activo,
        usuario_id=UUID(current_user.sub),
    )
    return ConfiguracionLealtadOut.model_validate(row)


async def otorgar_puntos(
    conn: asyncpg.Connection,
    sucursal_id: UUID,
    celular: str,
    total_pagado: Decimal,
    usuario_id: UUID,
    comanda_id: UUID | None = None,
    reservacion_id: UUID | None = None,
    registro_id: UUID | None = None,
) -> int:
    """Otorga puntos por un pago (venta de caja, anticipo de reservación, o
    check-in de niños), si el programa está activo en esa sucursal y ese
    origen en particular no está desactivado. Exactamente uno de
    comanda_id/reservacion_id/registro_id debe venir, según el origen del
    pago. total_pagado debe ser el monto neto ya cobrado (después de
    cualquier descuento por canje aplicado en el mismo pago), para no
    otorgar puntos sobre dinero que el cliente no pagó. No-op (retorna 0) si
    no hay configuración, el programa o el origen están desactivados, o el
    cálculo da 0 puntos.

    Los puntos se escalan por valor_punto para no perder el cashback en
    pagos chicos: con valor_punto=0.01 (1 punto = 1 centavo), $85 al 1%
    ($0.85 de cashback) otorga 85 puntos en vez de truncarse a 0."""
    if sum(x is not None for x in (comanda_id, reservacion_id, registro_id)) != 1:
        raise ValueError(
            "Debe indicarse exactamente uno de comanda_id, reservacion_id o registro_id."
        )

    config = await lealtad_repository.obtener_configuracion(conn, sucursal_id)
    if not config or not config["activo"]:
        return 0
    if comanda_id is not None and not config["otorga_puntos_comandas"]:
        return 0
    if reservacion_id is not None and not config["otorga_puntos_reservaciones"]:
        return 0
    if registro_id is not None and not config["otorga_puntos_checkin"]:
        return 0

    cashback = total_pagado * Decimal(str(config["porcentaje_retorno"])) / 100
    valor_punto = Decimal(str(config["valor_punto"]))
    puntos = int((cashback / valor_punto).to_integral_value(rounding=ROUND_HALF_UP))
    if puntos <= 0:
        return 0

    fecha_caducidad = datetime.now(UTC) + timedelta(days=config["dias_caducidad"])
    lote = await lealtad_repository.crear_lote(
        conn,
        sucursal_id,
        celular,
        puntos,
        fecha_caducidad,
        usuario_id,
        comanda_id=comanda_id,
        reservacion_id=reservacion_id,
        registro_id=registro_id,
    )
    saldo = await lealtad_repository.calcular_saldo(conn, sucursal_id, celular)
    await lealtad_repository.registrar_movimiento(
        conn,
        sucursal_id,
        celular,
        lote["id"],
        comanda_id,
        "O",
        puntos,
        saldo,
        None,
        usuario_id,
        reservacion_id=reservacion_id,
        registro_id=registro_id,
    )
    return puntos


async def redimir_puntos(
    conn: asyncpg.Connection,
    sucursal_id: UUID,
    celular: str,
    puntos: int,
    comanda_id: UUID | None,
    usuario_id: UUID,
    registro_id: UUID | None = None,
) -> Decimal:
    """Consume `puntos` de los lotes vigentes del celular en esta sucursal,
    FIFO por fecha de caducidad (primero el más próximo a vencer). Bloquea
    las filas tocadas (FOR UPDATE) para que dos canjes concurrentes del
    mismo celular no sobre-consuman. Retorna el descuento en pesos
    (puntos * valor_punto vigente). comanda_id/registro_id son solo
    referencia para el ledger de auditoría (no hay CHECK de "exactamente
    uno" en movimientos_puntos, a diferencia de lotes_puntos)."""
    config = await lealtad_repository.obtener_configuracion(conn, sucursal_id)
    if not config:
        raise DatosInvalidos("No hay configuración de lealtad para esta sucursal.")

    lotes = await lealtad_repository.lotes_vigentes_for_update(conn, sucursal_id, celular)
    disponible = sum(lote["puntos_disponibles"] for lote in lotes)
    if disponible < puntos:
        raise SaldoInsuficienteError(disponible)

    restante = puntos
    saldo_actual = disponible
    for lote in lotes:
        if restante <= 0:
            break
        consumir = min(lote["puntos_disponibles"], restante)
        await lealtad_repository.descontar_lote(conn, lote["id"], consumir)
        restante -= consumir
        saldo_actual -= consumir
        await lealtad_repository.registrar_movimiento(
            conn,
            sucursal_id,
            celular,
            lote["id"],
            comanda_id,
            "R",
            -consumir,
            saldo_actual,
            None,
            usuario_id,
            registro_id=registro_id,
        )

    return puntos * Decimal(str(config["valor_punto"]))


async def revertir_por_cancelacion(
    conn: asyncpg.Connection, comanda_id: UUID, usuario_id: UUID | None
) -> None:
    """Si la comanda cancelada había otorgado un lote de puntos y sigue
    intacto (nadie redimió nada de él), lo anula. Si ya se redimió parcial
    o total, no se puede revertir limpiamente (ya se entregó el descuento) —
    se deja el lote como está y solo se registra un movimiento de auditoría,
    sin bloquear la cancelación de la comanda."""
    lote = await lealtad_repository.obtener_lote_por_comanda(conn, comanda_id)
    if lote is None:
        return

    if lote["puntos_disponibles"] != lote["puntos_otorgados"]:
        saldo = await lealtad_repository.calcular_saldo(conn, lote["sucursal_id"], lote["celular"])
        await lealtad_repository.registrar_movimiento(
            conn,
            lote["sucursal_id"],
            lote["celular"],
            lote["id"],
            comanda_id,
            "A",
            0,
            saldo,
            "Comanda cancelada con puntos ya redimidos; no se pudo revertir automáticamente.",
            usuario_id,
        )
        return

    await lealtad_repository.anular_lote(conn, lote["id"])
    saldo = await lealtad_repository.calcular_saldo(conn, lote["sucursal_id"], lote["celular"])
    await lealtad_repository.registrar_movimiento(
        conn,
        lote["sucursal_id"],
        lote["celular"],
        lote["id"],
        comanda_id,
        "C",
        -lote["puntos_otorgados"],
        saldo,
        None,
        usuario_id,
    )


async def consultar_saldo(
    conn: asyncpg.Connection, current_user: TokenData, sucursal_id: UUID | None, celular: str
) -> SaldoPuntosOut:
    scope = resolver_sucursal(current_user, sucursal_id)
    saldo = await lealtad_repository.calcular_saldo(conn, scope, celular)
    return SaldoPuntosOut(sucursal_id=scope, celular=celular, saldo=saldo)


async def listar_movimientos(
    conn: asyncpg.Connection,
    current_user: TokenData,
    sucursal_id: UUID | None,
    celular: str,
    desde: date | None,
    hasta: date | None,
) -> list[MovimientoPuntoOut]:
    scope = resolver_sucursal(current_user, sucursal_id)
    rows = await lealtad_repository.listar_movimientos(conn, scope, celular, desde, hasta)
    return [MovimientoPuntoOut.model_validate(r) for r in rows]


async def obtener_reporte(
    conn: asyncpg.Connection, current_user: TokenData, sucursal_id: UUID | None
) -> ReporteLealtadOut:
    scope = resolver_sucursal(current_user, sucursal_id)
    data = await lealtad_repository.reporte_agregado(conn, scope)
    return ReporteLealtadOut(sucursal_id=scope, **data)
