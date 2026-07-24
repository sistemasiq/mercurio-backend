from __future__ import annotations

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.api.deps import require_permission
from app.core.database import get_db
from app.schemas.auth import TokenData
from app.schemas.permission import (
    PermisoResponse,
    RolConPermisosResponse,
    RolCreateRequest,
    RolUpdateRequest,
    UpdateRolPermisosRequest,
)
from app.services.permission_service import (
    PermisoInvalidoError,
    RolNombreDuplicadoError,
    RolNotFoundError,
    RolProtegidoError,
    create_rol,
    get_rol,
    list_permisos,
    list_roles,
    update_rol,
    update_rol_permisos,
)

router = APIRouter(prefix="/api/permisos", tags=["Permisos"])

_NOT_FOUND = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail={"code": "ROL_NOT_FOUND", "message": "Rol no encontrado."},
)
_NOMBRE_DUPLICADO = HTTPException(
    status_code=status.HTTP_409_CONFLICT,
    detail={"code": "ROL_NOMBRE_DUPLICADO", "message": "Ya existe un rol con ese nombre."},
)
_PROTEGIDO = HTTPException(
    status_code=status.HTTP_403_FORBIDDEN,
    detail={
        "code": "ROL_PROTEGIDO",
        "message": "Este rol es estructural y no se puede modificar de esta forma.",
    },
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
    except RolProtegidoError:
        raise _PROTEGIDO from None
    except PermisoInvalidoError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "PERMISO_INVALIDO",
                "message": "Uno o más IDs de permiso no existen.",
            },
        ) from None


@router.post("/roles", response_model=RolConPermisosResponse, status_code=status.HTTP_201_CREATED)
async def post_rol(
    body: RolCreateRequest,
    _: TokenData = Depends(require_permission("permisos:editar")),
    conn: asyncpg.Connection = Depends(get_db),
) -> RolConPermisosResponse:
    try:
        return await create_rol(conn, body.nombre, body.descripcion, body.permiso_ids)
    except RolNombreDuplicadoError:
        raise _NOMBRE_DUPLICADO from None
    except PermisoInvalidoError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "PERMISO_INVALIDO",
                "message": "Uno o más IDs de permiso no existen.",
            },
        ) from None


@router.patch("/roles/{rol_id}", response_model=RolConPermisosResponse)
async def patch_rol(
    rol_id: int,
    body: RolUpdateRequest,
    _: TokenData = Depends(require_permission("permisos:editar")),
    conn: asyncpg.Connection = Depends(get_db),
) -> RolConPermisosResponse:
    try:
        return await update_rol(conn, rol_id, body)
    except RolNotFoundError:
        raise _NOT_FOUND from None
    except RolProtegidoError:
        raise _PROTEGIDO from None
    except RolNombreDuplicadoError:
        raise _NOMBRE_DUPLICADO from None


@router.get("/catalogo", response_model=list[PermisoResponse])
async def get_permisos(
    _: TokenData = Depends(require_permission("permisos:ver")),
    conn: asyncpg.Connection = Depends(get_db),
) -> list[PermisoResponse]:
    return await list_permisos(conn)


# Endpoint de uso interno: fuerza recarga del caché (útil en multi-instancia)
# @router.post("/cache/reload", status_code=status.HTTP_204_NO_CONTENT)
@router.post("/cache/reload", status_code=status.HTTP_200_OK)
async def reload_cache_endpoint(
    _: TokenData = Depends(require_permission("permisos:editar")),
    conn: asyncpg.Connection = Depends(get_db),
) -> Response:
    from app.services.permission_service import load_cache

    await load_cache(conn)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
