"""
app/api/routers/cajas_admin.py
CRUD administrativo de cajas físicas (/api/cajas).
Filtrado automático por la sucursal del usuario autenticado.
"""

from __future__ import annotations

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import require_permission
from app.core.database import get_db
from app.repositories.caja_repository import (
    actualizar_caja_admin,
    crear_caja_admin,
    eliminar_caja_admin,
    get_caja_admin_por_id,
    listar_cajas_admin,
)
from app.schemas.auth import TokenData
from app.schemas.horarios_cajas import CajaAdminCreate, CajaAdminResponse, CajaAdminUpdate

router = APIRouter(prefix="/api/cajas", tags=["Cajas (Admin)"])

_NOT_FOUND = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail={"code": "CAJA_NOT_FOUND", "message": "Caja no encontrada."},
)

_SIN_SUCURSAL = HTTPException(
    status_code=status.HTTP_400_BAD_REQUEST,
    detail={"code": "SIN_SUCURSAL", "message": "El usuario no tiene sucursal asignada."},
)

_NUMERO_DUPLICADO = HTTPException(
    status_code=status.HTTP_409_CONFLICT,
    detail={"code": "NUMERO_DUPLICADO", "message": "Ya existe una caja activa con ese número en esta sucursal."},
)


def _branch_id(current_user: TokenData) -> str:
    if not current_user.branch_id:
        raise _SIN_SUCURSAL
    return str(current_user.branch_id)


@router.get("", response_model=list[CajaAdminResponse], summary="Lista las cajas de la sucursal")
async def listar(
    current_user: TokenData = Depends(require_permission("cajas:listar")),
    conn: asyncpg.Connection = Depends(get_db),
) -> list[CajaAdminResponse]:
    rows = await listar_cajas_admin(conn, sucursal_id=_branch_id(current_user))
    return [CajaAdminResponse(**r) for r in rows]


@router.post(
    "",
    response_model=CajaAdminResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crea una nueva caja en la sucursal del usuario",
)
async def crear(
    payload: CajaAdminCreate,
    current_user: TokenData = Depends(require_permission("cajas:crear")),
    conn: asyncpg.Connection = Depends(get_db),
) -> CajaAdminResponse:
    try:
        row = await crear_caja_admin(
            conn,
            sucursal_id=_branch_id(current_user),
            nombre=payload.nombre,
            numero=payload.numero,
            creado_por=current_user.sub,
        )
    except Exception as exc:
        if "unique" in str(exc).lower():
            raise _NUMERO_DUPLICADO from exc
        raise
    return CajaAdminResponse(**row)


@router.patch(
    "/{caja_id}",
    response_model=CajaAdminResponse,
    summary="Edita una caja de la sucursal",
)
async def editar(
    caja_id: str,
    payload: CajaAdminUpdate,
    current_user: TokenData = Depends(require_permission("cajas:editar")),
    conn: asyncpg.Connection = Depends(get_db),
) -> CajaAdminResponse:
    sucursal_id = _branch_id(current_user)

    existing = await get_caja_admin_por_id(conn, caja_id)
    if existing is None or existing["sucursal_id"] != sucursal_id:
        raise _NOT_FOUND

    try:
        row = await actualizar_caja_admin(
            conn,
            caja_id=caja_id,
            nombre=payload.nombre,
            numero=payload.numero,
            activo=payload.activo,
            modificado_por=current_user.sub,
        )
    except Exception as exc:
        if "unique" in str(exc).lower():
            raise _NUMERO_DUPLICADO from exc
        raise
    if row is None:
        raise _NOT_FOUND
    return CajaAdminResponse(**row)


@router.delete(
    "/{caja_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    summary="Desactiva una caja de la sucursal (borrado lógico)",
)
async def eliminar(
    caja_id: str,
    current_user: TokenData = Depends(require_permission("cajas:eliminar")),
    conn: asyncpg.Connection = Depends(get_db),
) -> None:
    sucursal_id = _branch_id(current_user)

    existing = await get_caja_admin_por_id(conn, caja_id)
    if existing is None or existing["sucursal_id"] != sucursal_id:
        raise _NOT_FOUND

    await eliminar_caja_admin(conn, caja_id=caja_id, modificado_por=current_user.sub)
