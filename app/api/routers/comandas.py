"""
app/api/routers/comandas.py
Router de comandas — solo valida entrada y delega al service.
SAD §3.2 / Regla 11.4: el router nunca accede a un repository ni escribe SQL.
"""

from __future__ import annotations

import logging
from dataclasses import asdict
from typing import Any
from uuid import UUID

import asyncpg
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from pydantic import BaseModel

from app.api.deps import get_current_user_ws, require_permission, require_role
from app.core.database import get_db
from app.core.scope import sucursal_scope
from app.core.ws_manager import CANAL_GLOBAL, manager
from app.schemas.auth import TokenData
from app.schemas.comanda import ComandaCreate, ComandaModifyRequest
from app.services import comanda_service
from app.services.permission_service import has_permission

logger = logging.getLogger("mercury.ws")

router = APIRouter(prefix="/api/comandas", tags=["Comandas"])


class CambioEstadoRequest(BaseModel):
    estado_actual: str
    motivo_cancelacion: str | None = None


def get_active_branch(current_user: TokenData) -> UUID:
    if current_user.branch_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="La sesión no tiene una sucursal activa.",
        )
    return current_user.branch_id


# ── Endpoints ────────────────────────────────────────────────────────────────


@router.post("", status_code=status.HTTP_201_CREATED)
async def crear_comanda(
    comanda_in: ComandaCreate,
    conn: asyncpg.Connection = Depends(get_db),
    current_user: TokenData = Depends(require_permission("restaurante:crear_pedido")),
) -> Any:
    """Crea una comanda nueva con sus detalles."""
    # Obtenemos la sucursal de forma centralizada y segura: nunca confiar en
    # el sucursal_id que mande el cliente en el body.
    active_branch_id = get_active_branch(current_user)
    comanda_in = comanda_in.model_copy(update={"sucursal_id": active_branch_id})

    try:
        comanda = await comanda_service.crear_comanda(conn, comanda_in, current_user)
        return asdict(comanda)
    except HTTPException:
        # Preserva el status code y el {code, message} estructurado de
        # excepciones como StockInsuficienteError — no las aplana a 400 str().
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get("")
async def listar_comandas(
    conn: asyncpg.Connection = Depends(get_db),
    current_user: TokenData = Depends(require_permission("restaurante:ver_pedidos")),
) -> Any:
    """Lista las comandas activas (P, E, L) de la sucursal del usuario, o de
    todas las sucursales si es AdministradorSistema."""
    comandas = await comanda_service.listar_pendientes(conn, current_user)
    return [asdict(c) for c in comandas]


@router.patch("/{comanda_id}/estado")
async def cambiar_estado(
    comanda_id: str,
    data: CambioEstadoRequest,
    conn: asyncpg.Connection = Depends(get_db),
    current_user: TokenData = Depends(
        require_role("AdministradorSistema", "Administrador", "Cajero", "Cocina")
    ),
) -> Any:
    """Actualiza el estado de una comanda con auditoría."""
    try:
        comanda = await comanda_service.cambiar_estado(
            conn,
            comanda_id,
            data.estado_actual,
            current_user,
            motivo_cancelacion=data.motivo_cancelacion,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    if comanda is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comanda no encontrada",
        )

    scope = sucursal_scope(current_user)
    canal = scope if scope is not None else CANAL_GLOBAL

    await manager.broadcast(
        canal,
        {"type": "comanda_actualizada", "comanda": asdict(comanda)},
    )

    return asdict(comanda)


@router.patch("/{comanda_id}/detalles")
async def modificar_detalles(
    comanda_id: str,
    data: ComandaModifyRequest,
    conn: asyncpg.Connection = Depends(get_db),
    current_user: TokenData = Depends(require_permission("restaurante:registrar_pago")),
) -> Any:
    """Elimina productos de una comanda en estado Pendiente y recalcula el total.

    Si se eliminan todos los productos, cancela automáticamente la comanda
    y requiere motivo_cancelacion en el body.
    """
    usuario_id = str(UUID(current_user.sub))
    try:
        comanda = await comanda_service.modificar_comanda_parcial(
            conn,
            comanda_id,
            data.detalles_ids_a_eliminar,
            usuario_id,
            data.motivo_cancelacion,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    if comanda is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La comanda no existe o no está en estado Pendiente.",
        )

    scope = sucursal_scope(current_user)
    canal = scope if scope is not None else CANAL_GLOBAL

    await manager.broadcast(
        canal,
        {"type": "comanda_actualizada", "comanda": asdict(comanda)},
    )

    return asdict(comanda)


@router.websocket("/ws")
async def comandas_ws(
    websocket: WebSocket,
    token: str = Query(...),
    conn: asyncpg.Connection = Depends(get_db),
) -> None:
    """Canal en tiempo real de comandas: emite comanda_creada/comanda_actualizada
    a los clientes de la sucursal correspondiente (ver app/core/ws_manager.py).

    El JWT viaja por query param porque el handshake WS nativo del navegador no
    admite headers custom (no se puede reusar require_permission tal cual)."""
    try:
        current_user = await get_current_user_ws(token, conn)
    except HTTPException:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    if not has_permission(current_user.role, "restaurante:ver_pedidos"):
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
        logger.debug("Conexion WS de comandas cerrada con error", exc_info=True)
        manager.disconnect(canal, websocket)
