from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import asyncpg

from app.core.roles import ROL_SISTEMA
from app.exceptions import DatosInvalidos, NoEncontrado
from app.repositories import lealtad_repository
from app.schemas.auth import TokenData
from app.schemas.lealtad import ConfiguracionLealtadBase, ConfiguracionLealtadOut


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
    comanda_id: UUID,
    total_pagado: Decimal,
    usuario_id: UUID,
) -> int:
    """Otorga puntos por una venta pagada, si el programa está activo en esa
    sucursal. total_pagado debe ser el monto neto ya cobrado (después de
    cualquier descuento por canje aplicado en la misma venta), para no
    otorgar puntos sobre dinero que el cliente no pagó. No-op (retorna 0) si
    no hay configuración, está inactiva, o el cálculo da 0 puntos."""
    config = await lealtad_repository.obtener_configuracion(conn, sucursal_id)
    if not config or not config["activo"]:
        return 0

    puntos = int(total_pagado * Decimal(str(config["porcentaje_retorno"])) / 100)
    if puntos <= 0:
        return 0

    fecha_caducidad = datetime.now(UTC) + timedelta(days=config["dias_caducidad"])
    lote = await lealtad_repository.crear_lote(
        conn, sucursal_id, celular, comanda_id, puntos, fecha_caducidad, usuario_id
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
    )
    return puntos


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
