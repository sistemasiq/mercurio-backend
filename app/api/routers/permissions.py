from __future__ import annotations

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.api.deps import require_permission
from app.core.database import get_db
from app.schemas.auth import TokenData
from app.schemas.permission import PermisoResponse, RolConPermisosResponse, UpdateRolPermisosRequest
from app.services.permission_service import (
    PermisoInvalidoError,
    RolNotFoundError,
    get_rol,
    list_permisos,
    list_roles,
    update_rol_permisos,
)

router = APIRouter(prefix="/api/permissions", tags=["permissions"])

_NOT_FOUND = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail={"code": "ROL_NOT_FOUND", "message": "Rol no encontrado."},
)


@router.get("/roles", response_model=list[RolConPermisosResponse])
async def get_roles(
    _: TokenData = Depends(require_permission("permisos:ver")),
    conn: asyncpg.Connection = Depends(get_db),
) -> list[RolConPermisosResponse]:
    return await list_roles(conn)


@router.get("/roles/{rol_id}", response_model=RolConPermisosResponse)
async def get_rol_endpoint(
    rol_id: int,
    _: TokenData = Depends(require_permission("permisos:ver")),
    conn: asyncpg.Connection = Depends(get_db),
) -> RolConPermisosResponse:
    try:
        return await get_rol(conn, rol_id)
    except RolNotFoundError:
        raise _NOT_FOUND from None


@router.put("/roles/{rol_id}", response_model=RolConPermisosResponse)
async def put_rol_permisos(
    rol_id: int,
    body: UpdateRolPermisosRequest,
    _: TokenData = Depends(require_permission("permisos:editar")),
    conn: asyncpg.Connection = Depends(get_db),
) -> RolConPermisosResponse:
    try:
        return await update_rol_permisos(conn, rol_id, body.permiso_ids)
    except RolNotFoundError:
        raise _NOT_FOUND from None
    except PermisoInvalidoError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "PERMISO_INVALIDO",
                "message": "Uno o más IDs de permiso no existen.",
            },
        ) from None


@router.get("/permisos", response_model=list[PermisoResponse])
async def get_permisos(
    _: TokenData = Depends(require_permission("permisos:ver")),
    conn: asyncpg.Connection = Depends(get_db),
) -> list[PermisoResponse]:
    return await list_permisos(conn)


# Endpoint de uso interno: fuerza recarga del caché (útil en multi-instancia)
#@router.post("/cache/reload", status_code=status.HTTP_204_NO_CONTENT)
@router.post("/cache/reload", status_code=status.HTTP_200_OK)
async def reload_cache_endpoint(
    _: TokenData = Depends(require_permission("permisos:editar")),
    conn: asyncpg.Connection = Depends(get_db),
) -> Response:
    from app.services.permission_service import load_cache

    await load_cache(conn)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
