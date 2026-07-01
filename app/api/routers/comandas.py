"""
app/api/routers/comandas.py
Router de comandas — solo valida entrada y delega al service.
SAD §3.2 / Regla 11.4: el router nunca accede a un repository ni escribe SQL.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.api.deps import get_current_user
from app.core.database import get_db
from app.schemas.auth import TokenData
from app.schemas.comanda import ComandaCreate
from app.services import comanda_service

router = APIRouter()


class CambioEstadoRequest(BaseModel):
    estado_actual: str


# ── Endpoints ────────────────────────────────────────────────────────────────


@router.post("/", status_code=status.HTTP_201_CREATED)
async def crear_comanda(
    comanda_in: ComandaCreate,
    conn: asyncpg.Connection = Depends(get_db),
    _: TokenData = Depends(get_current_user),
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
    _: TokenData = Depends(get_current_user),
) -> Any:
    """Lista todas las comandas activas (P, E, L)."""
    comandas = await comanda_service.listar_pendientes(conn)
    return [asdict(c) for c in comandas]


@router.patch("/{comanda_id}/estado")
async def cambiar_estado(
    comanda_id: str,
    data: CambioEstadoRequest,
    conn: asyncpg.Connection = Depends(get_db),
    _: TokenData = Depends(get_current_user),
) -> Any:
    """Actualiza el estado de una comanda."""
    comanda = await comanda_service.cambiar_estado(conn, comanda_id, data.estado_actual)
    if comanda is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comanda no encontrada",
        )
    return {"message": "Estado actualizado con éxito"}
