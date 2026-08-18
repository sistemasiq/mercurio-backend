"""
app/api/routers/turnos_caja.py
Endpoints FastAPI para el módulo de Cierre de Caja (/api/turnos-caja).
"""

from __future__ import annotations

import asyncpg
from fastapi import APIRouter, Depends, Query, Response, status

from app.api.deps import get_current_user, require_permission
from app.core.database import get_db
from app.schemas.auth import TokenData
from app.schemas.caja import (
    AbrirTurnoPayload,
    CajaResponse,
    ConfirmarCierrePayload,
    ConfirmarCierreResponse,
    ConteoPayload,
    DetalleArqueoResponse,
    FiltrosHistorial,
    HistorialArqueosResponse,
    MetodoPagoTurnoResponse,
    RetiroParcialCreate,
    RetiroParcialResponse,
    RevisionAdminPayload,
    RevisionAdminResponse,
    TurnoActivoResponse,
    TurnoResponse,
)
from app.services import turnos_caja_service
from app.services.pdf_service import generar_pdf_arqueo

router = APIRouter(prefix="/api/turnos-caja", tags=["Turnos de Caja"])


@router.get(
    "/turnos",
    response_model=list[TurnoResponse],
    summary="Lista los turnos horarios configurados",
)
async def listar_turnos(
    current_user: TokenData = Depends(require_permission("turnos_caja:ver_activo")),
    conn: asyncpg.Connection = Depends(get_db),
) -> list[TurnoResponse]:
    return await turnos_caja_service.obtener_turnos(conn)


@router.get(
    "/cajas",
    response_model=list[CajaResponse],
    summary="Lista las cajas registradas (filtra por sucursal si se indica)",
)
async def listar_cajas(
    sucursal_id: str | None = Query(None),
    _: TokenData = Depends(require_permission("cajas:listar")),
    conn: asyncpg.Connection = Depends(get_db),
) -> list[CajaResponse]:
    return await turnos_caja_service.obtener_cajas(conn, sucursal_id)


@router.post(
    "/abrir",
    response_model=TurnoActivoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Abre un nuevo turno de caja para el cajero autenticado",
)
async def abrir_turno(
    payload: AbrirTurnoPayload,
    current_user: TokenData = Depends(require_permission("turnos_caja:abrir")),
    conn: asyncpg.Connection = Depends(get_db),
) -> TurnoActivoResponse:
    branch_id = str(current_user.branch_id) if current_user.branch_id else None
    return await turnos_caja_service.abrir_turno(
        conn,
        user_id=current_user.sub,
        branch_id=branch_id,
        payload=payload,
    )


@router.get(
    "/activo",
    response_model=TurnoActivoResponse,
    summary="Obtiene el turno activo del cajero autenticado",
)
async def obtener_activo(
    sucursal_id: str | None = Query(None),
    current_user: TokenData = Depends(require_permission("turnos_caja:ver_activo")),
    conn: asyncpg.Connection = Depends(get_db),
) -> TurnoActivoResponse:
    # AdministradorSistema no tiene sucursal propia: la apertura activa debe
    # respetar la sucursal elegida en el selector global, no cualquier turno
    # abierto en otra sucursal. El resto de roles siempre usa su propia
    # sucursal del JWT, sin importar qué sucursal_id se mande por query param
    # (mismo criterio que /historial, ver _sucursal_restringida).
    if current_user.role == "AdministradorSistema":
        sucursal_efectiva = sucursal_id
    else:
        sucursal_efectiva = str(current_user.branch_id) if current_user.branch_id else None
    return await turnos_caja_service.obtener_turno_activo(conn, current_user.sub, sucursal_efectiva)


@router.get(
    "/activo/metodos-pago",
    response_model=list[MetodoPagoTurnoResponse],
    summary="Métodos de pago que tienen movimientos en el turno activo del cajero",
)
async def obtener_metodos_pago_activo(
    current_user: TokenData = Depends(require_permission("turnos_caja:ver_activo")),
    conn: asyncpg.Connection = Depends(get_db),
) -> list[MetodoPagoTurnoResponse]:
    return await turnos_caja_service.obtener_metodos_pago_activo(conn, current_user.sub)


@router.post(
    "/iniciar-conteo",
    response_model=TurnoActivoResponse,
    summary="Transiciona el turno a EN_CORTE (inicio de conteo físico)",
)
async def iniciar_conteo(
    body: dict,
    current_user: TokenData = Depends(require_permission("turnos_caja:conteo")),
    conn: asyncpg.Connection = Depends(get_db),
) -> TurnoActivoResponse:
    turno_id = body.get("turno_id", "")
    return await turnos_caja_service.iniciar_conteo(conn, current_user.sub, turno_id)


@router.post(
    "/conteo",
    response_model=TurnoActivoResponse,
    summary="Envía la declaración física del cajero y guarda los montos declarados",
)
async def enviar_conteo(
    payload: ConteoPayload,
    current_user: TokenData = Depends(require_permission("turnos_caja:conteo")),
    conn: asyncpg.Connection = Depends(get_db),
) -> TurnoActivoResponse:
    return await turnos_caja_service.enviar_conteo(conn, current_user.sub, payload)


@router.post(
    "/revision-admin",
    response_model=RevisionAdminResponse,
    summary="Valida credenciales del administrador y revela el balance real",
)
async def autenticar_revision_admin(
    payload: RevisionAdminPayload,
    current_user: TokenData = Depends(require_permission("turnos_caja:revision_admin")),
    conn: asyncpg.Connection = Depends(get_db),
) -> RevisionAdminResponse:
    return await turnos_caja_service.autenticar_admin_revision(conn, current_user.sub, payload)


@router.post(
    "/confirmar",
    response_model=ConfirmarCierreResponse,
    summary="Confirma el cierre definitivo del turno usando el token temporal del admin",
)
async def confirmar_cierre(
    payload: ConfirmarCierrePayload,
    current_user: TokenData = Depends(require_permission("turnos_caja:confirmar")),
    conn: asyncpg.Connection = Depends(get_db),
) -> ConfirmarCierreResponse:
    return await turnos_caja_service.confirmar_cierre(conn, current_user.sub, payload)


@router.post(
    "/validar-pin-cajero",
    summary="Valida el PIN del cajero contra la base de datos",
)
async def validar_pin_cajero(
    body: dict,
    current_user: TokenData = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db),
) -> dict:
    turno_id = body.get("turno_id", "")
    pin = body.get("pin", "")
    return await turnos_caja_service.validar_pin_cajero(conn, current_user.sub, turno_id, pin)


@router.post(
    "/validar-pin-admin",
    summary="Valida el PIN del administrador contra la base de datos",
)
async def validar_pin_admin(
    body: dict,
    current_user: TokenData = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db),
) -> dict:
    turno_id = body.get("turno_id", "")
    admin_email = body.get("admin_email", "")
    pin = body.get("pin", "")
    return await turnos_caja_service.validar_pin_admin(conn, turno_id, admin_email, pin)


@router.post(
    "/cancelar",
    response_model=TurnoActivoResponse,
    summary="Cancela el conteo en curso y regresa el turno a ABIERTA",
)
async def cancelar_conteo(
    body: dict,
    current_user: TokenData = Depends(require_permission("turnos_caja:cancelar")),
    conn: asyncpg.Connection = Depends(get_db),
) -> TurnoActivoResponse:
    turno_id = body.get("turno_id", "")
    return await turnos_caja_service.cancelar_conteo(conn, current_user.sub, turno_id)


@router.post(
    "/retiro",
    response_model=RetiroParcialResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registra un retiro parcial sobre el turno activo (solo en estado OPERANDO)",
)
async def registrar_retiro(
    payload: RetiroParcialCreate,
    current_user: TokenData = Depends(require_permission("retiros_parciales:crear")),
    conn: asyncpg.Connection = Depends(get_db),
) -> RetiroParcialResponse:
    return await turnos_caja_service.crear_retiro(conn, current_user.sub, payload)


@router.get(
    "/{turno_id}/retiros",
    response_model=list[RetiroParcialResponse],
    summary="Lista los retiros parciales registrados en el turno",
)
async def listar_retiros(
    turno_id: str,
    current_user: TokenData = Depends(require_permission("retiros_parciales:listar")),
    conn: asyncpg.Connection = Depends(get_db),
) -> list[RetiroParcialResponse]:
    return await turnos_caja_service.listar_retiros(conn, turno_id)


@router.get(
    "/historial",
    response_model=HistorialArqueosResponse,
    summary="Lista el historial de arqueos de caja con filtros opcionales",
)
async def listar_historial(
    sucursal_id: str | None = Query(None),
    cajero_id: str | None = Query(None),
    fecha_desde: str | None = Query(None),
    fecha_hasta: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: TokenData = Depends(require_permission("turnos_caja:historial")),
    conn: asyncpg.Connection = Depends(get_db),
) -> HistorialArqueosResponse:
    # Un Administrador de sucursal o Cajero solo puede ver su propia sucursal, sin importar
    # qué sucursal_id se haya mandado por query param. Solo AdministradorSistema ve todas.
    if current_user.role == "AdministradorSistema":
        sucursal_efectiva = sucursal_id
    else:
        sucursal_efectiva = str(current_user.branch_id) if current_user.branch_id else None

    filtros = FiltrosHistorial(
        sucursal_id=sucursal_efectiva,
        cajero_id=cajero_id,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        page=page,
        page_size=page_size,
    )
    return await turnos_caja_service.listar_historial(conn, filtros)


def _sucursal_restringida(current_user: TokenData) -> str | None:
    """None para AdministradorSistema (acceso global); el branch_id propio para el resto."""
    if current_user.role == "AdministradorSistema":
        return None
    return str(current_user.branch_id) if current_user.branch_id else None


@router.get(
    "/historial/{cierre_id}",
    response_model=DetalleArqueoResponse,
    summary="Detalle completo de un arqueo de caja",
)
async def obtener_detalle_arqueo(
    cierre_id: str,
    current_user: TokenData = Depends(require_permission("turnos_caja:historial")),
    conn: asyncpg.Connection = Depends(get_db),
) -> DetalleArqueoResponse:
    return await turnos_caja_service.obtener_detalle(
        conn, cierre_id, sucursal_id=_sucursal_restringida(current_user)
    )


@router.get(
    "/historial/{cierre_id}/pdf",
    summary="Descarga el PDF de comprobante de arqueo",
)
async def descargar_pdf(
    cierre_id: str,
    current_user: TokenData = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db),
) -> Response:
    detalle = await turnos_caja_service.obtener_detalle(
        conn, cierre_id, sucursal_id=_sucursal_restringida(current_user)
    )
    pdf_bytes = generar_pdf_arqueo(detalle)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=arqueo_{cierre_id}.pdf"},
    )
