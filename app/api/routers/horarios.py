"""
app/api/routers/horarios.py
CRUD administrativo de horarios/turnos de trabajo (/api/horarios).
"""

from __future__ import annotations

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import require_permission
from app.core.database import get_db
from app.repositories.horarios_repository import (
    actualizar_horario,
    crear_horario,
    eliminar_horario,
    listar_horarios,
)
from app.schemas.auth import TokenData
from app.schemas.horarios_cajas import HorarioCreate, HorarioResponse, HorarioUpdate

router = APIRouter(prefix="/api/horarios", tags=["Horarios"])

_NOT_FOUND = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail={"code": "HORARIO_NOT_FOUND", "message": "Horario no encontrado."},
)

_NOMBRE_DUPLICADO = HTTPException(
    status_code=status.HTTP_409_CONFLICT,
    detail={"code": "NOMBRE_DUPLICADO", "message": "Ya existe un horario con ese nombre."},
)


@router.get("", response_model=list[HorarioResponse], summary="Lista los horarios de trabajo")
async def listar(
    current_user: TokenData = Depends(require_permission("horarios:listar")),
    conn: asyncpg.Connection = Depends(get_db),
) -> list[HorarioResponse]:
    rows = await listar_horarios(conn)
    return [HorarioResponse(**r) for r in rows]


@router.post(
    "",
    response_model=HorarioResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crea un nuevo horario de trabajo",
)
async def crear(
    payload: HorarioCreate,
    current_user: TokenData = Depends(require_permission("horarios:crear")),
    conn: asyncpg.Connection = Depends(get_db),
) -> HorarioResponse:
    try:
        row = await crear_horario(
            conn,
            nombre=payload.nombre,
            hora_inicio=payload.hora_inicio,
            hora_fin=payload.hora_fin,
            creado_por=current_user.sub,
        )
    except Exception as exc:
        if "unique" in str(exc).lower() and "nombre" in str(exc).lower():
            raise _NOMBRE_DUPLICADO from exc
        raise
    return HorarioResponse(**row)


@router.patch(
    "/{horario_id}",
    response_model=HorarioResponse,
    summary="Edita un horario de trabajo existente",
)
async def editar(
    horario_id: str,
    payload: HorarioUpdate,
    current_user: TokenData = Depends(require_permission("horarios:editar")),
    conn: asyncpg.Connection = Depends(get_db),
) -> HorarioResponse:
    try:
        row = await actualizar_horario(
            conn,
            horario_id=horario_id,
            nombre=payload.nombre,
            hora_inicio=payload.hora_inicio,
            hora_fin=payload.hora_fin,
            activo=payload.activo,
            modificado_por=current_user.sub,
        )
    except Exception as exc:
        if "unique" in str(exc).lower() and "nombre" in str(exc).lower():
            raise _NOMBRE_DUPLICADO from exc
        raise
    if row is None:
        raise _NOT_FOUND
    return HorarioResponse(**row)


@router.delete(
    "/{horario_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    summary="Desactiva un horario de trabajo (borrado lógico)",
)
async def eliminar(
    horario_id: str,
    current_user: TokenData = Depends(require_permission("horarios:eliminar")),
    conn: asyncpg.Connection = Depends(get_db),
) -> None:
    found = await eliminar_horario(conn, horario_id=horario_id, modificado_por=current_user.sub)
    if not found:
        raise _NOT_FOUND
