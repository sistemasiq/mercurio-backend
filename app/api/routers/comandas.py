"""
app/api/routers/comandas.py
Router de comandas — solo valida entrada y delega al service.
SAD §3.2 / Regla 11.4: el router nunca accede a un repository ni escribe SQL.
"""

from __future__ import annotations

import logging
from dataclasses import asdict
from typing import Any

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

from app.api.deps import get_current_user_ws, require_permission
from app.core.database import get_db
from app.core.ws_manager import CANAL_GLOBAL, manager
from app.schemas.auth import TokenData
from app.schemas.comanda import ComandaCreate
from app.services import comanda_service
from app.services.permission_service import has_permission

logger = logging.getLogger("mercury.ws")

router = APIRouter(prefix="/api/comandas", tags=["comandas"])


class CambioEstadoRequest(BaseModel):
    estado_actual: str


# ── Endpoints ────────────────────────────────────────────────────────────────


@router.post("/", status_code=status.HTTP_201_CREATED)
async def crear_comanda(
    comanda_in: ComandaCreate,
    conn: asyncpg.Connection = Depends(get_db),
    _: TokenData = Depends(require_permission("restaurante:crear_pedido")),
) -> Any:
    """Crea una comanda nueva con sus detalles."""
    try:
        comanda = await comanda_service.crear_comanda(conn, comanda_in)
        return asdict(comanda)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get("/")
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
    current_user: TokenData = Depends(require_permission("restaurante:gestionar_cocina")),
) -> Any:
    """Actualiza el estado de una comanda."""
    comanda = await comanda_service.cambiar_estado(conn, comanda_id, data.estado_actual)
    if comanda is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comanda no encontrada",
        )

    scope = comanda_service.sucursal_scope(current_user)
    canal = scope if scope is not None else CANAL_GLOBAL

    await manager.broadcast(
        canal,
        {"tipo": "comanda_actualizada", "comanda": asdict(comanda)},
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

    if not has_permission(current_user.role.value, "restaurante:ver_pedidos"):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    scope = comanda_service.sucursal_scope(current_user)
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
