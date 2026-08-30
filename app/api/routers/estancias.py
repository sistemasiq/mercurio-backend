import logging
from typing import Any
from uuid import UUID

import asyncpg
from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from pydantic import ValidationError
from starlette import status

from app.api.deps import apertura_operando_id, get_current_user_ws, require_permission
from app.core.database import get_db
from app.core.scope import sucursal_scope
from app.core.ws_manager import CANAL_GLOBAL, manager
from app.schemas.auth import TokenData
from app.schemas.pagos import PagoEstanciaExtraRequest
from app.schemas.registros import (
    CheckoutRequest,
    CheckoutResponse,
    CotizacionCheckoutResponse,
    DetalleActivoResponse,
    OnboardingRequest,
    OnboardingResponse,
    ProductoResponse,
)
from app.services.chekouts import cotizar_checkout, create_chekout
from app.services.estancias import (
    create_estancia,
    get_activos_estancia_by_sucursal_id,
    get_productos_estancia_by_id_sucursal,
)
from app.services.pagos_estancia import pago_create_service
from app.services.permission_service import has_permission

logger = logging.getLogger("mercury.ws")

router = APIRouter(prefix="/api/estancias", tags=["Estancias"])


@router.get(
    "/activos/{sucursal_id}",
    response_model=list[DetalleActivoResponse],
    summary="Listar niños en estancia",
    description="Consulta todos los niños que se encuentran activos actualmente en la sucursal.",
)
async def get_activos(
    sucursal_id: UUID,
    conn: asyncpg.Connection = Depends(get_db),
    current_user: TokenData = Depends(require_permission("estancias:ver_activos")),
) -> list[dict[str, Any]]:

    scope = sucursal_scope(current_user)
    if scope is not None and str(sucursal_id) != scope:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No puede consultar estancias de otra sucursal.",
        )
    return await get_activos_estancia_by_sucursal_id(conn, sucursal_id)


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=OnboardingResponse,
    summary="Registrar entrada de niños",
    description=(
        "Crea un registro de entrada completo vinculando al tutor, "
        "los niños y procesando el pago inicial."
    ),
)
async def onboarding(
    fotoIne: UploadFile = File(...),  # noqa: N803 - nombre del campo multipart del front
    fotoLlegada: UploadFile = File(...),  # noqa: N803 - nombre del campo multipart del front
    payload: str = Form(..., description="JSON string con los datos de OnboardingRequest"),
    conn: asyncpg.Connection = Depends(get_db),
    current_user: TokenData = Depends(require_permission("estancias:checkin")),
    apertura_id: str = Depends(apertura_operando_id),
) -> dict[str, Any]:
    try:
        data = OnboardingRequest.model_validate_json(payload)
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=e.errors()) from e

    usuario_id = UUID(current_user.sub)

    return await create_estancia(conn, data, fotoIne, fotoLlegada, usuario_id, apertura_id)


@router.post(
    "/{registro_id}/pagos",
    status_code=status.HTTP_201_CREATED,
    summary="Registrar pago adicional",
    description=(
        "Registra uno o más pagos extraordinarios vinculados "
        "a un registro de estancia existente."
    ),
)
async def pago_estancia_extra(
    registro_id: UUID,
    body: PagoEstanciaExtraRequest,
    sucursal_id: UUID,
    conn: asyncpg.Connection = Depends(get_db),
    current_user: TokenData = Depends(require_permission("estancias:gestionar_pagos")),
    apertura_id: str = Depends(apertura_operando_id),
) -> None:
    usuario_id = UUID(current_user.sub)
    return await pago_create_service(conn, body, sucursal_id, registro_id, usuario_id, apertura_id)


# Endpoint para cotizar el checkout (solo lectura, no registra nada)
@router.get(
    "/{detalle_id}/checkout/cotizacion",
    response_model=CotizacionCheckoutResponse,
    summary="Cotizar cargo extra de checkout",
    description=(
        "Calcula cuánto se debería cobrar por tiempo excedido en este momento, "
        "sin registrar la salida ni el cargo. Úsalo para mostrarle el monto al "
        "cajero antes de cobrar (al entrar a la pantalla y de nuevo justo antes "
        "de confirmar la salida, ya que el monto puede cambiar con el tiempo)."
    ),
)
async def get_cotizacion_checkout(
    detalle_id: UUID,
    conn: asyncpg.Connection = Depends(get_db),
    _: TokenData = Depends(require_permission("estancias:checkout")),
) -> dict[str, Any]:
    return await cotizar_checkout(conn, detalle_id)


# Endpoint para calcular checkout
@router.post(
    "/{detalle_id}/checkout",
    status_code=status.HTTP_201_CREATED,
    response_model=CheckoutResponse,
    summary="Procesar salida del niño",
    description=(
        "Registra la salida, calcula cargos extra por tiempo y marca "
        "el registro como finalizado si corresponde. Si hay cargo extra, "
        "'pagos' debe cubrir exactamente el monto recalculado en este momento "
        "(ver /checkout/cotizacion) o se rechaza con 409."
    ),
)
async def checkout(
    detalle_id: UUID,
    body: CheckoutRequest,
    conn: asyncpg.Connection = Depends(get_db),
    current_user: TokenData = Depends(require_permission("estancias:checkout")),
    apertura_id: str = Depends(apertura_operando_id),
) -> dict[str, Any]:
    usuario_id = UUID(current_user.sub)

    return await create_chekout(
        conn, detalle_id, body.pulseraTutorId, usuario_id, body.pagos, apertura_id
    )


@router.get(
    "/productos/{sucursal_id}",
    response_model=list[ProductoResponse],
    summary="Listar productos",
    description="Obtiene el catálogo de productos tipo 'estancia' activos para la sucursal.",
)
async def get_productos(
    sucursal_id: UUID,
    conn: asyncpg.Connection = Depends(get_db),
    _: TokenData = Depends(require_permission("estancias:checkin")),
) -> list[dict[str, Any]]:
    return await get_productos_estancia_by_id_sucursal(conn, sucursal_id)


@router.websocket("/ws")
async def estancias_ws(
    websocket: WebSocket,
    token: str = Query(...),
    conn: asyncpg.Connection = Depends(get_db),
) -> None:
    """Canal en tiempo real de estancias: emite estancia_creada/estancia_checkout
    a los clientes de la sucursal correspondiente (ver app/core/ws_manager.py),
    para refrescar Control de Acceso sin necesidad de polling.

    El JWT viaja por query param porque el handshake WS nativo del navegador no
    admite headers custom (no se puede reusar require_permission tal cual)."""
    try:
        current_user = await get_current_user_ws(token, conn)
    except HTTPException:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    if not has_permission(current_user.role, "estancias:ver_activos"):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    scope = sucursal_scope(current_user)
    canal = scope if scope is not None else CANAL_GLOBAL

    await manager.connect(canal, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(canal, websocket)
    except Exception:
        logger.debug("Conexion WS de estancias cerrada con error", exc_info=True)
        manager.disconnect(canal, websocket)
