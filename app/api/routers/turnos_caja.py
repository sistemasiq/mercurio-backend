"""
app/api/routers/turnos_caja.py
Endpoints FastAPI para el módulo de Cierre de Caja (/turnos-caja).
"""

from __future__ import annotations

import asyncpg
from fastapi import APIRouter, Depends, Query, Response, status
from fastapi.responses import StreamingResponse

from app.api.deps import get_current_user
from app.core.database import get_db
from app.schemas.auth import TokenData
from app.schemas.caja import (
    AbrirTurnoPayload,
    TurnoActivoResponse,
    ConteoPayload,
    RevisionAdminPayload,
    RevisionAdminResponse,
    ConfirmarCierrePayload,
    ConfirmarCierreResponse,
    FiltrosHistorial,
    HistorialArqueosResponse,
    DetalleArqueoResponse,
    TurnoResponse,
    CajaResponse,
)
from app.services import turnos_caja_service

router = APIRouter(prefix="/api/turnos-caja", tags=["Turnos de Caja"])


@router.get(
    "/turnos",
    response_model=list[TurnoResponse],
    summary="Obtiene la lista de turnos configurados en la base de datos",
)
async def listar_turnos(
    conn: asyncpg.Connection = Depends(get_db),
) -> list[TurnoResponse]:
    return await turnos_caja_service.obtener_turnos(conn)


@router.get(
    "/cajas",
    response_model=list[CajaResponse],
    summary="Obtiene la lista de cajas registradas en la base de datos",
)
async def listar_cajas(
    sucursal_id: str | None = Query(None),
    conn: asyncpg.Connection = Depends(get_db),
) -> list[CajaResponse]:
    return await turnos_caja_service.obtener_cajas(conn, sucursal_id)


@router.post(
    "/abrir",
    response_model=TurnoActivoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Abre un nuevo turno de caja",
)
async def abrir_turno(
    payload: AbrirTurnoPayload,
    current_user: TokenData = Depends(get_current_user),
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
    summary="Obtiene el turno de caja activo para el cajero",
)
async def obtener_activo(
    current_user: TokenData = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db),
) -> TurnoActivoResponse:
    return await turnos_caja_service.obtener_turno_activo(conn, current_user.sub)


@router.post(
    "/iniciar-conteo",
    response_model=TurnoActivoResponse,
    summary="Transiciona el turno a EN_CONTEO",
)
async def iniciar_conteo(
    body: dict,
    current_user: TokenData = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db),
) -> TurnoActivoResponse:
    turno_id = body.get("turno_id", "")
    return await turnos_caja_service.iniciar_conteo(conn, current_user.sub, turno_id)


@router.post(
    "/conteo",
    response_model=TurnoActivoResponse,
    summary="Envía la declaración física del cajero",
)
async def enviar_conteo(
    payload: ConteoPayload,
    current_user: TokenData = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db),
) -> TurnoActivoResponse:
    return await turnos_caja_service.enviar_conteo(conn, current_user.sub, payload)


@router.post(
    "/revision-admin",
    response_model=RevisionAdminResponse,
    summary="Valida credenciales del administrador y revela el balance",
)
async def autenticar_revision_admin(
    payload: RevisionAdminPayload,
    current_user: TokenData = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db),
) -> RevisionAdminResponse:
    return await turnos_caja_service.autenticar_admin_revision(conn, current_user.sub, payload)


@router.post(
    "/confirmar",
    response_model=ConfirmarCierreResponse,
    summary="Confirma el cierre definitivo del turno y genera arqueo",
)
async def confirmar_cierre(
    payload: ConfirmarCierrePayload,
    current_user: TokenData = Depends(get_current_user),
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
):
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
):
    turno_id = body.get("turno_id", "")
    admin_email = body.get("admin_email", "")
    pin = body.get("pin", "")
    return await turnos_caja_service.validar_pin_admin(conn, turno_id, admin_email, pin)


@router.post(
    "/cancelar",
    response_model=TurnoActivoResponse,
    summary="Cancela el conteo en curso y regresa a OPERANDO",
)
async def cancelar_conteo(
    body: dict,
    current_user: TokenData = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db),
) -> TurnoActivoResponse:
    turno_id = body.get("turno_id", "")
    return await turnos_caja_service.cancelar_conteo(conn, current_user.sub, turno_id)


@router.get(
    "/historial",
    response_model=HistorialArqueosResponse,
    summary="Lista histórica de arqueos de caja",
)
async def listar_historial(
    sucursal_id: str | None = Query(None),
    cajero_id: str | None = Query(None),
    fecha_desde: str | None = Query(None),
    fecha_hasta: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: TokenData = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db),
) -> HistorialArqueosResponse:
    filtros = FiltrosHistorial(
        sucursal_id=sucursal_id or (str(current_user.branch_id) if current_user.branch_id else None),
        cajero_id=cajero_id,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        page=page,
        page_size=page_size,
    )
    return await turnos_caja_service.listar_historial(conn, filtros)


@router.get(
    "/historial/{cierre_id}",
    response_model=DetalleArqueoResponse,
    summary="Obtiene el detalle completo de un arqueo de caja",
)
async def obtener_detalle_arqueo(
    cierre_id: str,
    current_user: TokenData = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db),
) -> DetalleArqueoResponse:
    return await turnos_caja_service.obtener_detalle(conn, cierre_id)


@router.get(
    "/historial/{cierre_id}/pdf",
    summary="Descarga el PDF de comprobante de arqueo",
)
async def descargar_pdf(
    cierre_id: str,
    current_user: TokenData = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db),
) -> Response:
    # Contenido dummy PDF mínimo válido para la descarga
    pdf_bytes = b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj 2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj 3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R>>endobj\nxref\n0 4\n0000000000 65535 f\n0000000009 00000 n\n0000000052 00000 n\n0000000115 00000 n\ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n185\n%%EOF"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=arqueo_{cierre_id}.pdf"},
    )
