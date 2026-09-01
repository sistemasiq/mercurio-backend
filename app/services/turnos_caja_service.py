"""
app/services/turnos_caja_service.py
Servicio de negocio para el módulo de Cierre de Caja.
Maneja las reglas de negocio (RN-APE, RN-CIE, RN-VAL), validaciones y segregación de funciones.
"""

from __future__ import annotations

import json
import uuid
from decimal import Decimal

import asyncpg
from fastapi import HTTPException, status

from app.core.security import verify_password
from app.repositories.caja_repository import (
    actualizar_admin_autorizacion,
    actualizar_conteo_apertura,
    actualizar_estado_apertura,
    contar_historial_cierres,
    crear_apertura_caja,
    crear_cierre_caja,
    crear_retiro_parcial,
    get_apertura_activa_por_caja,
    get_apertura_activa_por_usuario,
    get_apertura_por_id,
    get_caja_por_codigo,
    listar_cajas_por_sucursal,
    listar_cambios_por_apertura,
    listar_historial_cierres,
    listar_retiros_por_apertura,
    listar_turnos,
    obtener_detalle_cierre,
    obtener_metodos_con_movimientos,
    obtener_movimientos_por_metodo,
    registrar_ingreso_efectivo,
    registrar_movimiento_caja,
    resetear_conteo_apertura,
    sumar_cambio_apertura,
    sumar_ingresos_por_apertura,
    sumar_retiros_por_apertura,
    sumar_total_ventas_apertura,
    sumar_ventas_efectivo_apertura,
)
from app.schemas.caja import (
    AbrirTurnoPayload,
    ArqueoResumen,
    CajaResponse,
    CambioResponse,
    ConfirmarCierrePayload,
    ConfirmarCierreResponse,
    ConteoPayload,
    DesgloseEfectivoDetalle,
    DetalleArqueoResponse,
    FilaBalance,
    FiltrosHistorial,
    HistorialArqueosResponse,
    IngresoEfectivoCreate,
    IngresoEfectivoResponse,
    MetodoPagoTurnoResponse,
    MovimientoResumen,
    RetiroParcialCreate,
    RetiroParcialResponse,
    RevisionAdminPayload,
    RevisionAdminResponse,
    TurnoActivoResponse,
    TurnoResponse,
)


class TurnoNoEncontradoError(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "TURNO_NO_ENCONTRADO", "message": "No se encontró un turno activo para esta sesión."},
        )


class TransicionInvalidaError(HTTPException):
    def __init__(self, mensaje: str):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "TRANSICION_INVALIDA", "message": mensaje},
        )


class CredencialesAdminInvalidasError(HTTPException):
    def __init__(self, mensaje: str = "Credenciales de administrador incorrectas."):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "CREDENCIALES_INVALIDAS", "message": mensaje},
        )


class SucursalNoAutorizadaError(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "SUCURSAL_NO_AUTORIZADA",
                "message": "No tienes permiso para consultar información de esta sucursal.",
            },
        )


async def obtener_cajas(conn: asyncpg.Connection, sucursal_id: str | None = None) -> list[CajaResponse]:
    rows = await listar_cajas_por_sucursal(conn, sucursal_id)
    return [
        CajaResponse(
            id=str(r["id"]),
            sucursal_id=str(r["sucursal_id"]),
            codigo=r["codigo"],
            nombre=r["nombre"],
            creado=r.get("creado"),
        )
        for r in rows
    ]


async def obtener_turnos(conn: asyncpg.Connection) -> list[TurnoResponse]:
    rows = await listar_turnos(conn)
    return [
        TurnoResponse(
            id=str(r["id"]),
            nombre=r["nombre"],
            hora_inicio=r["hora_inicio"],
            hora_fin=r["hora_fin"],
        )
        for r in rows
    ]


async def abrir_turno(
    conn: asyncpg.Connection,
    user_id: str,
    branch_id: str | None,
    payload: AbrirTurnoPayload,
) -> TurnoActivoResponse:
    sucursal = branch_id or payload.sucursal_id

    # 1. Verificar si el usuario ya tiene turno activo (RN-APE-001)
    activa = await get_apertura_activa_por_usuario(conn, user_id)
    if activa:
        if sucursal and str(activa["sucursal_id"]) != str(sucursal):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "TURNO_ACTIVO_OTRA_SUCURSAL",
                    "message": (
                        f"Ya tienes un turno abierto en {activa['sucursal_nombre']}. "
                        "Ciérralo antes de abrir uno en otra sucursal."
                    ),
                },
            )
        return await obtener_turno_activo(conn, user_id, sucursal)

    if not sucursal:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "SUCURSAL_REQUERIDA",
                "message": "Debes especificar la sucursal en la que se abrirá la caja.",
            },
        )
    if not payload.terminal:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "TERMINAL_REQUERIDA", "message": "Debes seleccionar una caja o terminal."},
        )

    caja = await get_caja_por_codigo(conn, sucursal, payload.terminal)
    if not caja:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "CAJA_NO_ENCONTRADA", "message": "La caja seleccionada no existe. Solicita al administrador que la registre."},
        )

    caja_id = str(caja["id"])

    # Verificar si la caja física ya tiene un turno abierto (RN-APE-002)
    caja_activa = await get_apertura_activa_por_caja(conn, caja_id)
    if caja_activa:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "CAJA_OCUPADA", "message": "La caja física seleccionada ya cuenta con un turno activo."},
        )

    if not payload.turno_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "TURNO_REQUERIDO", "message": "Debes seleccionar un turno de trabajo."},
        )
    turno_id = payload.turno_id

    # Crear la apertura
    nueva = await crear_apertura_caja(
        conn,
        caja_id=caja_id,
        cajero_id=user_id,
        turno_id=turno_id,
        fondo_inicial=payload.fondo_inicial,
        creado_por=user_id,
    )

    return TurnoActivoResponse(
        id=str(nueva["id"]),
        sucursal_id=str(nueva["sucursal_id"]),
        sucursal_nombre=str(nueva["sucursal_nombre"]),
        cajero_id=str(nueva["cajero_id"]),
        cajero_nombre=str(nueva["cajero_nombre"]),
        terminal=str(nueva["terminal"]),
        estado="OPERANDO",
        fondo_inicial=Decimal(str(nueva["fondo_inicial"])),
        fecha_apertura=str(nueva["fecha_apertura"]),
        total_ventas=Decimal("0"),
        total_retiros=Decimal("0"),
        movimientos=[],
    )


async def obtener_turno_activo(
    conn: asyncpg.Connection, user_id: str, sucursal_id: str | None = None
) -> TurnoActivoResponse:
    activa = await get_apertura_activa_por_usuario(conn, user_id, sucursal_id)
    if not activa:
        raise TurnoNoEncontradoError()

    apertura_id = str(activa["id"])
    total_ventas = await sumar_total_ventas_apertura(conn, apertura_id)
    total_retiros = await sumar_retiros_por_apertura(conn, apertura_id)
    movs_raw = await obtener_movimientos_por_metodo(conn, apertura_id)

    movimientos = [
        MovimientoResumen(metodo=r["metodo_nombre"].lower(), total_ventas=Decimal(str(r["total_ventas"])))
        for r in movs_raw
    ]

    # apertura_caja.estado solo distingue ABIERTA/EN_CORTE/CERRADA — el sub-estado real
    # de EN_CORTE (¿el cajero ya envió su conteo y quedó congelado, o todavía lo está
    # llenando?) se infiere de monto_declarado. Sin esto, recargar la página después de
    # enviar el conteo mostraba otra vez el formulario vacío en vez del modal de espera
    # del administrador, y un segundo "Enviar conteo" chocaba con el ya congelado.
    if activa["estado"] != "EN_CORTE":
        estado_ui = "OPERANDO"
    elif activa["monto_declarado"] is None:
        estado_ui = "EN_CONTEO"
    else:
        estado_ui = "ESPERANDO_REVISION"

    return TurnoActivoResponse(
        id=apertura_id,
        sucursal_id=str(activa["sucursal_id"]),
        sucursal_nombre=str(activa["sucursal_nombre"]),
        cajero_id=str(activa["cajero_id"]),
        cajero_nombre=str(activa["cajero_nombre"]),
        terminal=str(activa["terminal"]),
        estado=estado_ui,
        fondo_inicial=Decimal(str(activa["fondo_inicial"])),
        fecha_apertura=str(activa["fecha_apertura"]),
        total_ventas=total_ventas,
        total_retiros=total_retiros,
        movimientos=movimientos,
    )


async def iniciar_conteo(conn: asyncpg.Connection, user_id: str, turno_id: str) -> TurnoActivoResponse:
    apertura = await get_apertura_por_id(conn, turno_id)
    if not apertura or str(apertura["cajero_id"]) != user_id:
        raise TurnoNoEncontradoError()

    if apertura["estado"] != "ABIERTA":
        raise TransicionInvalidaError(
            "Solo se puede iniciar el conteo desde un turno operando (ABIERTA)."
        )

    await actualizar_estado_apertura(conn, turno_id, "EN_CORTE")
    return await obtener_turno_activo(conn, user_id)


async def enviar_conteo(conn: asyncpg.Connection, user_id: str, payload: ConteoPayload) -> TurnoActivoResponse:
    apertura = await get_apertura_por_id(conn, payload.turno_id)
    if not apertura or str(apertura["cajero_id"]) != user_id:
        raise TurnoNoEncontradoError()

    if apertura["estado"] != "EN_CORTE":
        raise TransicionInvalidaError("Debes iniciar el conteo antes de enviar la declaración.")

    # RN-VAL-001: una vez enviado el conteo queda congelado hasta que se cancele explícitamente.
    if apertura["monto_declarado"] is not None:
        raise TransicionInvalidaError(
            "El conteo ya fue enviado y está congelado esperando revisión del administrador."
        )

    conteo_json = json.dumps(
        {
            "desglose_efectivo": payload.desglose_efectivo.model_dump(mode="json"),
            "metodos_pago": [m.model_dump(mode="json") for m in payload.metodos_pago],
        }
    )
    await actualizar_conteo_apertura(conn, payload.turno_id, payload.total_declarado, conteo_json)
    await actualizar_estado_apertura(conn, payload.turno_id, "EN_CORTE")
    res = await obtener_turno_activo(conn, user_id)
    res.estado = "ESPERANDO_REVISION"
    return res


async def _calcular_balance(
    conn: asyncpg.Connection, apertura: dict, turno_id: str
) -> tuple[Decimal, Decimal, Decimal, list[FilaBalance]]:
    """Balance real del cierre. Devuelve dos vistas distintas:
    - `balance` (por método): el renglón "efectivo" compara el dinero físico —
      fondo inicial + ventas en efectivo (o sin método aún, ver
      sumar_ventas_efectivo_apertura) + ingresos de efectivo - retiros -
      cambio dado — contra lo que el cajero contó físicamente
      (desglose_efectivo.total en conteo_json). Cada otro método compara lo
      que el sistema registró contra lo que el cajero declaró para ese
      método específico.
    - Totales generales (esperado/declarado/diferencia): todos los métodos de
      pago cuentan como dinero real del sistema (cupones, lealtad, vouchers
      incluidos) — es la suma de todos los movimientos del turno + fondo
      inicial + ingresos de efectivo - retiros - cambio dado, comparada
      contra la suma de todo lo que el cajero declaró, independientemente
      del método."""
    monto_inicial = Decimal(str(apertura["fondo_inicial"]))
    total_retiros = await sumar_retiros_por_apertura(conn, turno_id)
    total_cambio = await sumar_cambio_apertura(conn, turno_id)
    total_ingresos = await sumar_ingresos_por_apertura(conn, turno_id)
    total_esperado_efectivo = (
        monto_inicial
        + await sumar_ventas_efectivo_apertura(conn, turno_id)
        + total_ingresos
        - total_retiros
        - total_cambio
    )

    conteo = json.loads(apertura["conteo_json"]) if apertura["conteo_json"] else {}
    declarado_efectivo = Decimal(str((conteo.get("desglose_efectivo") or {}).get("total", 0)))

    declarados_por_metodo: dict[str, Decimal] = {}
    for m in conteo.get("metodos_pago") or []:
        nombre = str(m.get("metodo", "")).strip().lower()
        if not nombre:
            continue
        monto = Decimal(str(m.get("monto", 0)))
        declarados_por_metodo[nombre] = declarados_por_metodo.get(nombre, Decimal("0")) + monto

    diferencia_neta_efectivo = declarado_efectivo - total_esperado_efectivo

    balance: list[FilaBalance] = [
        FilaBalance(
            metodo="efectivo",
            label="Efectivo en Caja",
            declarado=declarado_efectivo,
            esperado=total_esperado_efectivo,
            diferencia=diferencia_neta_efectivo,
        )
    ]

    movs = await obtener_movimientos_por_metodo(conn, turno_id)
    vistos: set[str] = set()
    for m in movs:
        if m["metodo_tipo"] == "E":
            continue
        nombre_met = m["metodo_nombre"].lower()
        vistos.add(nombre_met)
        esperado = Decimal(str(m["total_ventas"]))
        declarado = declarados_por_metodo.get(nombre_met, Decimal("0"))
        balance.append(
            FilaBalance(
                metodo=nombre_met,
                label=m["metodo_nombre"],
                declarado=declarado,
                esperado=esperado,
                diferencia=declarado - esperado,
            )
        )

    # Métodos que el cajero declaró pero el sistema no tiene registrados para este turno.
    for nombre_met, declarado in declarados_por_metodo.items():
        if nombre_met in vistos or nombre_met == "efectivo":
            continue
        balance.append(
            FilaBalance(
                metodo=nombre_met,
                label=nombre_met.capitalize(),
                declarado=declarado,
                esperado=Decimal("0"),
                diferencia=declarado,
            )
        )

    # Totales generales (a diferencia del renglón "efectivo" de arriba, que sigue
    # comparando solo lo físico): a petición de Emilio, todo método de pago cuenta como
    # dinero real del sistema — cupones, lealtad y vouchers también son dinero — así que
    # el total esperado/declarado/diferencia que ve el administrador para autorizar suma
    # todos los métodos con movimientos en el turno, no solo efectivo.
    total_esperado_general = (
        monto_inicial
        + await sumar_total_ventas_apertura(conn, turno_id)
        + total_ingresos
        - total_retiros
        - total_cambio
    )
    total_declarado_general = declarado_efectivo + sum(
        declarados_por_metodo.values(), Decimal("0")
    )
    diferencia_neta_general = total_declarado_general - total_esperado_general

    return total_esperado_general, total_declarado_general, diferencia_neta_general, balance


async def _verificar_credenciales_usuario(conn: asyncpg.Connection, email: str, password: str) -> asyncpg.Record:
    """Busca el usuario por email y verifica su contraseña o PIN contra la BD.
    Lanza CredencialesAdminInvalidasError si no existe o las credenciales son incorrectas."""
    row = await conn.fetchrow(
        """
        SELECT u.id, u.email, u.password_hash, u.pin_hash, u.nombre_completo, us.sucursal_id
        FROM public.usuarios u
        LEFT JOIN public.usuarios_sucursal us ON us.usuario_id = u.id AND us.activo = TRUE
        WHERE u.email = $1 AND u.activo = TRUE
        LIMIT 1
        """,
        email,
    )
    if not row:
        raise CredencialesAdminInvalidasError("Usuario no encontrado.")

    pass_ok = verify_password(password, row["password_hash"])
    pin_ok = bool(row["pin_hash"]) and verify_password(password, row["pin_hash"])

    if not pass_ok and not pin_ok:
        raise CredencialesAdminInvalidasError("Contraseña o PIN incorrecto.")

    return row


async def autenticar_admin_revision(
    conn: asyncpg.Connection,
    user_id: str,
    payload: RevisionAdminPayload,
) -> RevisionAdminResponse:
    admin_row = await _verificar_credenciales_usuario(conn, payload.admin_email, payload.admin_password)

    # 3. Calcular montos esperados reales para el turno
    apertura = await get_apertura_por_id(conn, payload.turno_id)
    if not apertura:
        raise TurnoNoEncontradoError()

    if apertura["estado"] == "CERRADA":
        raise TransicionInvalidaError("Este turno ya fue cerrado anteriormente.")

    # Validar que el administrador pertenezca a la misma sucursal de la caja
    admin_sucursal = admin_row.get("sucursal_id")
    turno_sucursal = apertura.get("sucursal_id")
    if admin_sucursal and turno_sucursal and str(admin_sucursal) != str(turno_sucursal):
        raise CredencialesAdminInvalidasError("El administrador no está asignado a esta sucursal.")

    if apertura["monto_declarado"] is None:
        raise TransicionInvalidaError("El cajero aún no ha enviado su declaración de conteo.")

    total_esperado, total_declarado, diferencia_neta, balance = await _calcular_balance(
        conn, apertura, payload.turno_id
    )

    await actualizar_admin_autorizacion(conn, payload.turno_id, str(admin_row["id"]))

    return RevisionAdminResponse(
        autorizado=True,
        admin_nombre=admin_row["nombre_completo"],
        total_esperado=total_esperado,
        total_declarado=total_declarado,
        diferencia_neta=diferencia_neta,
        balance_por_metodo=balance,
    )


async def validar_pin_cajero(
    conn: asyncpg.Connection,
    user_id: str,
    turno_id: str,
    pin: str,
) -> dict:
    apertura = await get_apertura_por_id(conn, turno_id)
    if not apertura:
        raise TurnoNoEncontradoError()

    cajero_row = await conn.fetchrow(
        """
        SELECT id, email, pin_hash, password_hash, nombre_completo
        FROM public.usuarios
        WHERE id = $1 AND activo = TRUE
        """,
        uuid.UUID(str(apertura["cajero_id"])),
    )
    if not cajero_row:
        raise CredencialesAdminInvalidasError("Usuario cajero no encontrado.")

    pin_ok = bool(cajero_row["pin_hash"]) and verify_password(pin, cajero_row["pin_hash"])
    if not pin_ok:
        pin_ok = verify_password(pin, cajero_row["password_hash"])

    if not pin_ok:
        raise CredencialesAdminInvalidasError("El PIN ingresado para el Cajero es incorrecto.")

    return {"ok": True, "mensaje": "PIN del Cajero verificado correctamente."}


async def validar_pin_admin(
    conn: asyncpg.Connection,
    turno_id: str,
    admin_email: str,
    pin: str,
) -> dict:
    apertura = await get_apertura_por_id(conn, turno_id)
    if not apertura:
        raise TurnoNoEncontradoError()

    admin_row = await conn.fetchrow(
        """
        SELECT u.id, u.pin_hash, u.password_hash, u.nombre_completo, us.sucursal_id
        FROM public.usuarios u
        LEFT JOIN public.usuarios_sucursal us ON us.usuario_id = u.id AND us.activo = TRUE
        WHERE u.email = $1 AND u.activo = TRUE
        LIMIT 1
        """,
        admin_email,
    )
    if not admin_row:
        raise CredencialesAdminInvalidasError("Administrador no encontrado.")

    pin_ok = bool(admin_row["pin_hash"]) and verify_password(pin, admin_row["pin_hash"])
    if not pin_ok:
        pin_ok = verify_password(pin, admin_row["password_hash"])

    if not pin_ok:
        raise CredencialesAdminInvalidasError("El PIN ingresado para el Administrador es incorrecto.")

    return {"ok": True, "mensaje": "PIN del Administrador verificado correctamente."}


async def cancelar_conteo(conn: asyncpg.Connection, user_id: str, turno_id: str) -> TurnoActivoResponse:
    apertura = await get_apertura_por_id(conn, turno_id)
    if not apertura:
        raise TurnoNoEncontradoError()

    if apertura["estado"] != "EN_CORTE":
        raise TransicionInvalidaError("Solo se puede cancelar un conteo en curso.")

    # RN-VAL-001: una vez que el admin autorizó la revisión, el cajero ya no puede cancelar.
    if apertura["token_admin_jti"] is not None:
        raise TransicionInvalidaError(
            "No se puede cancelar: la revisión del administrador ya fue autorizada."
        )

    await resetear_conteo_apertura(conn, turno_id)
    await actualizar_estado_apertura(conn, turno_id, "ABIERTA")
    return await obtener_turno_activo(conn, user_id)


async def obtener_apertura_operando_id(conn: asyncpg.Connection, user_id: str) -> str:
    """RN-APE-005 / RN-CIE-001: sin turno de caja en OPERANDO (ABIERTA), no se permite
    ninguna venta/cobro — ni sin apertura, ni durante conteo/revisión/cierre.
    Devuelve el id de la apertura activa para que el llamador registre el movimiento."""
    apertura = await get_apertura_activa_por_usuario(conn, user_id)
    if not apertura or apertura["estado"] != "ABIERTA":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "TURNO_NO_ABIERTO",
                "message": "Debes tener un turno de caja abierto (operando) para registrar ventas o pagos.",
            },
        )
    return str(apertura["id"])


async def verificar_turno_abierto(conn: asyncpg.Connection, user_id: str) -> None:
    """Igual que obtener_apertura_operando_id, para llamadores que solo necesitan el bloqueo."""
    await obtener_apertura_operando_id(conn, user_id)


async def crear_retiro(
    conn: asyncpg.Connection, user_id: str, payload: RetiroParcialCreate
) -> RetiroParcialResponse:
    apertura = await get_apertura_por_id(conn, payload.apertura_caja_id)
    if not apertura or str(apertura["cajero_id"]) != user_id:
        raise TurnoNoEncontradoError()

    if apertura["estado"] != "ABIERTA":
        raise TransicionInvalidaError(
            "No se pueden registrar retiros mientras el turno está en conteo o cierre."
        )

    async with conn.transaction():
        row = await crear_retiro_parcial(
            conn,
            apertura_caja_id=payload.apertura_caja_id,
            concepto=payload.concepto.value,
            tipo_destinatario=payload.tipo_destinatario.value,
            monto=payload.monto,
            observaciones=payload.observaciones,
            creado_por=user_id,
        )
        # retiros_parciales.id es bigint, pero movimientos_caja.referencia_id es uuid —
        # no hay forma de referenciar la fila del retiro directamente. Se usa el id de la
        # apertura (siempre uuid válido); para ubicar el retiro exacto, cruzar por
        # apertura_caja_id + tipo_movimiento='RP' + creado contra retiros_parciales.
        await registrar_movimiento_caja(
            conn,
            apertura_caja_id=payload.apertura_caja_id,
            tipo_movimiento="RP",
            referencia_id=payload.apertura_caja_id,
            metodo_pago_id=None,
            monto=payload.monto,
            creado_por=user_id,
        )
    return RetiroParcialResponse(
        id=str(row["id"]),
        apertura_caja_id=str(row["apertura_caja_id"]),
        concepto=row["concepto"],
        tipo_destinatario=row["tipo_destinatario"],
        monto=Decimal(str(row["monto"])),
        observaciones=row["observaciones"],
        creado=row["creado"],
    )


async def listar_retiros(conn: asyncpg.Connection, turno_id: str) -> list[RetiroParcialResponse]:
    rows = await listar_retiros_por_apertura(conn, turno_id)
    return [
        RetiroParcialResponse(
            id=str(r["id"]),
            apertura_caja_id=str(r["apertura_caja_id"]),
            concepto=r["concepto"],
            tipo_destinatario=r["tipo_destinatario"],
            monto=Decimal(str(r["monto"])),
            observaciones=r["observaciones"],
            creado=r["creado"],
        )
        for r in rows
    ]


async def crear_ingreso(
    conn: asyncpg.Connection, user_id: str, payload: IngresoEfectivoCreate
) -> IngresoEfectivoResponse:
    apertura = await get_apertura_por_id(conn, payload.apertura_caja_id)
    if not apertura or str(apertura["cajero_id"]) != user_id:
        raise TurnoNoEncontradoError()

    if apertura["estado"] != "ABIERTA":
        raise TransicionInvalidaError(
            "No se pueden registrar ingresos de efectivo mientras el turno está en conteo o cierre."
        )

    row = await registrar_ingreso_efectivo(
        conn,
        apertura_caja_id=payload.apertura_caja_id,
        referencia_id=payload.apertura_caja_id,
        monto=payload.monto,
        creado_por=user_id,
    )
    return IngresoEfectivoResponse(
        id=str(row["id"]),
        apertura_caja_id=str(row["apertura_caja_id"]),
        monto=Decimal(str(row["monto"])),
        creado=row["creado"],
    )


async def confirmar_cierre(
    conn: asyncpg.Connection,
    user_id: str,
    payload: ConfirmarCierrePayload,
) -> ConfirmarCierreResponse:
    apertura = await get_apertura_por_id(conn, payload.turno_id)
    if not apertura:
        raise TurnoNoEncontradoError()

    if apertura["estado"] == "CERRADA":
        raise TransicionInvalidaError("Este turno ya fue cerrado anteriormente.")

    if apertura["monto_declarado"] is None:
        raise TransicionInvalidaError("El cajero aún no ha enviado su declaración de conteo.")

    if apertura["token_admin_jti"] is None:
        raise TransicionInvalidaError("Aún no se ha autorizado la revisión de un administrador.")

    admin_id = str(apertura["token_admin_jti"])
    total_esperado, total_declarado, diferencia_neta, balance = await _calcular_balance(
        conn, apertura, payload.turno_id
    )

    # Las observaciones son siempre opcionales, haya o no diferencia — el cajero/admin
    # las agrega si quiere dejar contexto, pero el sistema no lo exige.

    # Crear el registro inmutable en cierre_caja
    cierre = await crear_cierre_caja(
        conn,
        apertura_caja_id=payload.turno_id,
        tipo_cierre=payload.tipo_cierre.value,
        monto_sistema=total_esperado,
        monto_cierre=total_declarado,
        cajero_id=str(apertura["cajero_id"]),
        administrador_id=admin_id,
        observaciones=payload.observaciones,
        creado_por=user_id,
    )

    # Transicionar el estado de la apertura a CERRADA (RN-VAL-007)
    await actualizar_estado_apertura(conn, payload.turno_id, "CERRADA")

    return ConfirmarCierreResponse(
        arqueo_id=str(cierre["id"]),
        estado="CERRADO",
        pdf_url=f"/api/turnos-caja/historial/{cierre['id']}/pdf",
        mensaje="Cierre confirmado correctamente.",
    )


async def obtener_metodos_pago_activo(
    conn: asyncpg.Connection, user_id: str
) -> list[MetodoPagoTurnoResponse]:
    activa = await get_apertura_activa_por_usuario(conn, user_id)
    if not activa:
        raise TurnoNoEncontradoError()

    rows = await obtener_metodos_con_movimientos(conn, str(activa["id"]))
    return [MetodoPagoTurnoResponse(id=str(r["id"]), nombre=r["nombre"]) for r in rows]


async def listar_historial(conn: asyncpg.Connection, filtros: FiltrosHistorial) -> HistorialArqueosResponse:
    offset = (filtros.page - 1) * filtros.page_size
    items_raw = await listar_historial_cierres(
        conn,
        sucursal_id=filtros.sucursal_id,
        cajero_id=filtros.cajero_id,
        offset=offset,
        limit=filtros.page_size,
    )
    total = await contar_historial_cierres(
        conn,
        sucursal_id=filtros.sucursal_id,
        cajero_id=filtros.cajero_id,
    )

    items = [
        ArqueoResumen(
            id=str(r["id"]),
            cajero_nombre=r["cajero_nombre"] or "—",
            terminal=r["terminal"],
            sucursal_nombre=r["sucursal_nombre"],
            fecha_apertura=str(r["fecha_apertura"]),
            fecha_cierre=str(r["fecha_cierre"]),
            fondo_inicial=Decimal(str(r["fondo_inicial"])),
            total_declarado=Decimal(str(r["total_declarado"])),
            total_esperado=Decimal(str(r["total_esperado"])),
            diferencia_neta=Decimal(str(r["diferencia_neta"])),
            tiene_observaciones=bool(r["tiene_observaciones"]),
            pdf_url=f"/api/turnos-caja/historial/{r['id']}/pdf",
            admin_nombre=r["admin_nombre"],
            tipo_cierre=r["tipo_cierre"],
        )
        for r in items_raw
    ]

    return HistorialArqueosResponse(
        items=items,
        total=total,
        page=filtros.page,
        page_size=filtros.page_size,
    )


async def obtener_detalle(
    conn: asyncpg.Connection, cierre_id: str, sucursal_id: str | None = None
) -> DetalleArqueoResponse:
    cierre = await obtener_detalle_cierre(conn, cierre_id)
    if not cierre:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "ARQUEO_NO_ENCONTRADO", "message": "El arqueo solicitado no existe."},
        )

    if sucursal_id and str(cierre["sucursal_id"]) != sucursal_id:
        raise SucursalNoAutorizadaError()

    apertura_caja_id = str(cierre["apertura_caja_id"])
    apertura = await get_apertura_por_id(conn, apertura_caja_id)
    _, _, _, balance = await _calcular_balance(conn, apertura, apertura_caja_id)
    retiros_raw = await listar_retiros_por_apertura(conn, apertura_caja_id)
    retiros = [
        RetiroParcialResponse(
            id=str(r["id"]),
            apertura_caja_id=str(r["apertura_caja_id"]),
            concepto=r["concepto"],
            tipo_destinatario=r["tipo_destinatario"],
            monto=Decimal(str(r["monto"])),
            observaciones=r["observaciones"],
            creado=r["creado"],
        )
        for r in retiros_raw
    ]

    cambios_raw = await listar_cambios_por_apertura(conn, apertura_caja_id)
    cambios = [
        CambioResponse(id=str(c["id"]), monto=Decimal(str(c["monto"])), creado=c["creado"])
        for c in cambios_raw
    ]

    return DetalleArqueoResponse(
        id=str(cierre["id"]),
        cajero_nombre=cierre["cajero_nombre"] or "—",
        terminal=cierre["terminal"],
        sucursal_nombre=cierre["sucursal_nombre"],
        fecha_apertura=str(cierre["fecha_apertura"]),
        fecha_cierre=str(cierre["fecha_cierre"]),
        fondo_inicial=Decimal(str(cierre["fondo_inicial"])),
        total_declarado=Decimal(str(cierre["total_declarado"])),
        total_esperado=Decimal(str(cierre["total_esperado"])),
        diferencia_neta=Decimal(str(cierre["diferencia_neta"])),
        tiene_observaciones=bool(cierre["observaciones"]),
        pdf_url=f"/api/turnos-caja/historial/{cierre['id']}/pdf",
        admin_nombre=cierre["admin_nombre"],
        tipo_cierre=cierre["tipo_cierre"],
        observaciones=cierre["observaciones"] or "",
        desglose_efectivo=DesgloseEfectivoDetalle(total=Decimal(str(cierre["total_declarado"]))),
        balance_por_metodo=balance,
        retiros=retiros,
        cambios=cambios,
    )
