"""
app/services/turnos_caja_service.py
Servicio de negocio para el módulo de Cierre de Caja.
"""

from __future__ import annotations

import json
import uuid
from datetime import timedelta
from decimal import Decimal

import asyncpg
from fastapi import HTTPException, status
from jose import JWTError

from app.core.security import create_access_token, decode_access_token, verify_password
from app.repositories.caja_repository import (
    actualizar_estado_apertura,
    contar_historial_cierres,
    crear_apertura_caja,
    crear_cierre_caja,
    crear_retiro_parcial,
    get_apertura_activa_por_caja,
    get_apertura_activa_por_usuario,
    get_apertura_por_id,
    get_caja_por_codigo,
    get_primer_turno,
    guardar_conteo,
    guardar_token_admin,
    invalidar_token_admin,
    listar_cajas_por_sucursal,
    listar_historial_cierres,
    listar_turnos,
    obtener_detalle_cierre,
    obtener_metodos_con_movimientos,
    obtener_movimientos_por_metodo,
    sumar_retiros_por_apertura,
    sumar_total_ventas_apertura,
    verificar_token_admin,
    crear_caja,
)
from app.schemas.caja import (
    AbrirTurnoPayload,
    ArqueoResumen,
    CajaResponse,
    ConfirmarCierrePayload,
    ConfirmarCierreResponse,
    DetalleArqueoResponse,
    DesgloseEfectivoDetalle,
    FilaBalance,
    FiltrosHistorial,
    HistorialArqueosResponse,
    MetodoPagoTurnoResponse,
    MovimientoResumen,
    ConteoPayload,
    RevisionAdminPayload,
    RevisionAdminResponse,
    TurnoActivoResponse,
    TurnoResponse,
)


class TurnoNoEncontradoError(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "TURNO_NO_ENCONTRADO", "message": "No se encontró un turno activo para esta sesión."},
        )


class TransicionInvalidaError(HTTPException):
    def __init__(self, mensaje: str) -> None:
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "TRANSICION_INVALIDA", "message": mensaje},
        )


class CredencialesAdminInvalidasError(HTTPException):
    def __init__(self, mensaje: str = "Credenciales de administrador incorrectas.") -> None:
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "CREDENCIALES_INVALIDAS", "message": mensaje},
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
    activa = await get_apertura_activa_por_usuario(conn, user_id)
    if activa:
        return await obtener_turno_activo(conn, user_id)

    sucursal = branch_id or "00000000-0000-0000-0000-000000000000"
    terminal_code = payload.terminal or "CAJA 01"

    caja = await get_caja_por_codigo(conn, sucursal, terminal_code)
    if not caja:
        caja = await crear_caja(conn, sucursal, terminal_code, f"Estación {terminal_code}", user_id)

    caja_id = str(caja["id"])

    caja_activa = await get_apertura_activa_por_caja(conn, caja_id)
    if caja_activa:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "CAJA_OCUPADA", "message": "La caja física seleccionada ya cuenta con un turno activo."},
        )

    if payload.turno_id:
        turno_id = payload.turno_id
    else:
        turno = await get_primer_turno(conn)
        assert turno is not None
        turno_id = str(turno["id"])

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


async def obtener_turno_activo(conn: asyncpg.Connection, user_id: str) -> TurnoActivoResponse:
    activa = await get_apertura_activa_por_usuario(conn, user_id)
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

    estado_ui = "EN_CONTEO" if activa["estado"] == "EN_CORTE" else "OPERANDO"

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

    if apertura["estado"] == "CERRADA":
        raise TransicionInvalidaError("El turno se encuentra cerrado.")

    await actualizar_estado_apertura(conn, turno_id, "EN_CORTE")
    return await obtener_turno_activo(conn, user_id)


async def enviar_conteo(conn: asyncpg.Connection, user_id: str, payload: ConteoPayload) -> TurnoActivoResponse:
    apertura = await get_apertura_por_id(conn, payload.turno_id)
    if not apertura or str(apertura["cajero_id"]) != user_id:
        raise TurnoNoEncontradoError()

    if apertura["estado"] != "EN_CORTE":
        raise TransicionInvalidaError("El conteo solo puede enviarse desde estado EN_CORTE.")

    conteo_json = payload.model_dump_json()
    await guardar_conteo(conn, payload.turno_id, conteo_json, payload.total_declarado)

    return await obtener_turno_activo(conn, user_id)


async def autenticar_admin_revision(
    conn: asyncpg.Connection,
    user_id: str,
    payload: RevisionAdminPayload,
) -> RevisionAdminResponse:
    admin_row = await conn.fetchrow(
        """
        SELECT u.id, u.email, u.password_hash, u.nombre_completo, u.pin_hash, us.sucursal_id
        FROM public.usuarios u
        LEFT JOIN public.usuarios_sucursal us ON us.usuario_id = u.id AND us.activo = TRUE
        WHERE u.email = $1 AND u.activo = TRUE
        LIMIT 1
        """,
        payload.admin_email,
    )

    if not admin_row:
        admin_row = await conn.fetchrow(
            """
            SELECT u.id, u.email, u.password_hash, u.nombre_completo, u.pin_hash, us.sucursal_id
            FROM public.usuarios u
            LEFT JOIN public.usuarios_sucursal us ON us.usuario_id = u.id AND us.activo = TRUE
            WHERE u.nombre_completo ILIKE $1 AND u.activo = TRUE
            LIMIT 1
            """,
            payload.admin_email,
        )

    if not admin_row:
        raise CredencialesAdminInvalidasError("Usuario de administrador no encontrado.")

    pass_ok = verify_password(payload.admin_password, admin_row["password_hash"])
    pin_ok = False
    if not pass_ok and admin_row["pin_hash"]:
        pin_ok = verify_password(payload.admin_password, admin_row["pin_hash"])

    if not pass_ok and not pin_ok:
        raise CredencialesAdminInvalidasError("Contraseña o PIN incorrecto.")

    apertura = await get_apertura_por_id(conn, payload.turno_id)
    if not apertura:
        raise TurnoNoEncontradoError()

    if apertura["estado"] != "EN_CORTE":
        raise TransicionInvalidaError("El turno debe estar en EN_CORTE para la revisión del administrador.")

    admin_sucursal = admin_row.get("sucursal_id")
    turno_sucursal = apertura.get("sucursal_id")
    if admin_sucursal and turno_sucursal and str(admin_sucursal) != str(turno_sucursal):
        raise CredencialesAdminInvalidasError("El administrador no está asignado a esta sucursal.")

    if not apertura.get("conteo_json"):
        raise TransicionInvalidaError("El cajero aún no ha enviado el conteo físico.")

    conteo_data = json.loads(apertura["conteo_json"])
    declared_by_method = {
        m["metodo"].lower(): Decimal(str(m["monto"]))
        for m in conteo_data.get("metodos_pago", [])
    }
    declarado_efectivo = Decimal(str(conteo_data["desglose_efectivo"]["total"]))
    total_declarado = Decimal(str(conteo_data.get("total_declarado", "0")))

    fondo_inicial = Decimal(str(apertura["fondo_inicial"]))
    total_retiros = await sumar_retiros_por_apertura(conn, payload.turno_id)
    movs = await obtener_movimientos_por_metodo(conn, payload.turno_id)
    total_ventas = sum((Decimal(str(m["total_ventas"])) for m in movs), Decimal("0"))
    total_esperado = fondo_inicial + total_ventas - total_retiros

    balance: list[FilaBalance] = []

    ventas_efectivo = sum(
        (Decimal(str(m["total_ventas"])) for m in movs if m["metodo_nombre"].lower() == "efectivo"),
        Decimal("0"),
    )
    esperado_efectivo = fondo_inicial + ventas_efectivo - total_retiros
    balance.append(
        FilaBalance(
            metodo="efectivo",
            label="Efectivo en Caja",
            declarado=declarado_efectivo,
            esperado=esperado_efectivo,
            diferencia=declarado_efectivo - esperado_efectivo,
        )
    )

    for m in movs:
        nombre_met = m["metodo_nombre"].lower()
        if nombre_met == "efectivo":
            continue
        esperado_met = Decimal(str(m["total_ventas"]))
        declarado_met = declared_by_method.get(nombre_met, Decimal("0"))
        balance.append(
            FilaBalance(
                metodo=nombre_met,
                label=m["metodo_nombre"],
                declarado=declarado_met,
                esperado=esperado_met,
                diferencia=declarado_met - esperado_met,
            )
        )

    # Emitir JWT temporal de un solo uso para el paso de confirmación
    admin_id_str = str(admin_row["id"])
    token = create_access_token(
        {"tipo": "admin_cierre", "apertura_caja_id": payload.turno_id, "sub": admin_id_str},
        expires_delta=timedelta(minutes=30),
    )
    token_payload = decode_access_token(token)
    jti = uuid.UUID(str(token_payload["jti"]))
    await guardar_token_admin(conn, payload.turno_id, jti)

    return RevisionAdminResponse(
        autorizado=True,
        admin_nombre=admin_row["nombre_completo"],
        total_esperado=total_esperado,
        total_declarado=total_declarado,
        diferencia_neta=total_declarado - total_esperado,
        balance_por_metodo=balance,
        temporal_auth_token=token,
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
        "SELECT id, pin_hash, password_hash, nombre_completo FROM public.usuarios WHERE id = $1 AND activo = TRUE",
        uuid.UUID(str(apertura["cajero_id"])),
    )
    if not cajero_row and user_id:
        cajero_row = await conn.fetchrow(
            "SELECT id, pin_hash, password_hash, nombre_completo FROM public.usuarios WHERE id = $1 AND activo = TRUE",
            uuid.UUID(user_id),
        )

    if not cajero_row:
        raise CredencialesAdminInvalidasError("Usuario cajero no encontrado en la base de datos.")

    pin_ok = False
    if cajero_row["pin_hash"]:
        pin_ok = verify_password(pin, cajero_row["pin_hash"])
    if not pin_ok and cajero_row["password_hash"]:
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

    turno_sucursal = apertura.get("sucursal_id")

    admin_row = None
    if admin_email and admin_email != "admin":
        admin_row = await conn.fetchrow(
            """
            SELECT u.id, u.pin_hash, u.password_hash, u.nombre_completo, us.sucursal_id
            FROM public.usuarios u
            LEFT JOIN public.usuarios_sucursal us ON us.usuario_id = u.id AND us.activo = TRUE
            WHERE (u.email ILIKE $1 OR u.nombre_completo ILIKE $1) AND u.activo = TRUE
            LIMIT 1
            """,
            admin_email,
        )

    if not admin_row and turno_sucursal:
        admin_row = await conn.fetchrow(
            """
            SELECT u.id, u.pin_hash, u.password_hash, u.nombre_completo, us.sucursal_id
            FROM public.usuarios u
            JOIN public.usuarios_sucursal us ON us.usuario_id = u.id AND us.activo = TRUE
            JOIN public.roles r ON r.id = u.rol
            WHERE us.sucursal_id = $1 AND u.activo = TRUE
              AND r.nombre IN ('Administrador', 'AdministradorSistema')
            LIMIT 1
            """,
            turno_sucursal,
        )

    if not admin_row:
        raise CredencialesAdminInvalidasError("Administrador de sucursal no encontrado en la base de datos.")

    pin_ok = False
    if admin_row["pin_hash"]:
        pin_ok = verify_password(pin, admin_row["pin_hash"])
    if not pin_ok and admin_row["password_hash"]:
        pin_ok = verify_password(pin, admin_row["password_hash"])

    if not pin_ok:
        raise CredencialesAdminInvalidasError("El PIN ingresado para el Administrador es incorrecto.")

    return {"ok": True, "mensaje": "PIN del Administrador verificado correctamente."}


async def cancelar_conteo(conn: asyncpg.Connection, user_id: str, turno_id: str) -> TurnoActivoResponse:
    apertura = await get_apertura_por_id(conn, turno_id)
    if not apertura or str(apertura["cajero_id"]) != user_id:
        raise TurnoNoEncontradoError()

    await actualizar_estado_apertura(conn, turno_id, "ABIERTA")
    return await obtener_turno_activo(conn, user_id)


async def confirmar_cierre(
    conn: asyncpg.Connection,
    user_id: str,
    payload: ConfirmarCierrePayload,
) -> ConfirmarCierreResponse:
    # Validar token temporal del administrador
    try:
        admin_token_payload = decode_access_token(payload.admin_token)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "TOKEN_INVALIDO", "message": "El token de autorización del administrador es inválido o ha expirado."},
        )

    if admin_token_payload.get("tipo") != "admin_cierre":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "TOKEN_INVALIDO", "message": "El token no corresponde a una autorización de cierre."},
        )

    if admin_token_payload.get("apertura_caja_id") != payload.turno_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "TOKEN_INVALIDO", "message": "El token no corresponde a este turno."},
        )

    token_jti = str(admin_token_payload.get("jti", ""))
    stored_jti = await verificar_token_admin(conn, payload.turno_id)
    if stored_jti is None or str(stored_jti) != token_jti:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "TOKEN_USADO", "message": "El token de administrador ya fue utilizado o no es válido."},
        )

    apertura = await get_apertura_por_id(conn, payload.turno_id)
    if not apertura:
        raise TurnoNoEncontradoError()

    if apertura["estado"] != "EN_CORTE":
        raise TransicionInvalidaError("El turno debe estar en EN_CORTE para poder cerrarse.")

    fondo_inicial = Decimal(str(apertura["fondo_inicial"]))
    total_ventas = await sumar_total_ventas_apertura(conn, payload.turno_id)
    total_retiros = await sumar_retiros_por_apertura(conn, payload.turno_id)
    monto_sistema = fondo_inicial + total_ventas - total_retiros

    monto_declarado = apertura.get("monto_declarado")
    if monto_declarado is None:
        monto_declarado = monto_sistema
    monto_cierre = Decimal(str(monto_declarado))

    admin_id = str(admin_token_payload.get("sub", user_id))

    cierre = await crear_cierre_caja(
        conn,
        apertura_caja_id=payload.turno_id,
        tipo_cierre=payload.tipo_cierre.value,
        monto_sistema=monto_sistema,
        monto_cierre=monto_cierre,
        cajero_id=str(apertura["cajero_id"]),
        administrador_id=admin_id,
        observaciones=payload.observaciones,
        creado_por=user_id,
    )

    # Invalidar el JTI para que el token no pueda reutilizarse
    await invalidar_token_admin(conn, payload.turno_id)
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
        )
        for r in items_raw
    ]

    return HistorialArqueosResponse(
        items=items,
        total=total,
        page=filtros.page,
        page_size=filtros.page_size,
    )


async def obtener_detalle(conn: asyncpg.Connection, cierre_id: str) -> DetalleArqueoResponse:
    cierre = await obtener_detalle_cierre(conn, cierre_id)
    if not cierre:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "ARQUEO_NO_ENCONTRADO", "message": "El arqueo solicitado no existe."},
        )

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
        observaciones=cierre["observaciones"] or "",
        desglose_efectivo=DesgloseEfectivoDetalle(total=Decimal(str(cierre["total_declarado"]))),
        balance_por_metodo=[],
    )
