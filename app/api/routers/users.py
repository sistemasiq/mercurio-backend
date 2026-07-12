from __future__ import annotations

from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.api.deps import require_permission
from app.core.database import get_db
from app.schemas.auth import TokenData
from app.schemas.user import UserCreateRequest, UserResponse, UserUpdateRequest
from app.services.user_service import (
    BranchRequiredError,
    EmailAlreadyExistsError,
    InsufficientPermissionsError,
    RolInvalidoError,
    UserNotFoundError,
    create_user,
    delete_user,
    get_user,
    list_users,
    update_user,
)

router = APIRouter(prefix="/api/usuarios", tags=["Usuarios"])

_NOT_FOUND = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail={"code": "USER_NOT_FOUND", "message": "Usuario no encontrado."},
)
_FORBIDDEN = HTTPException(
    status_code=status.HTTP_403_FORBIDDEN,
    detail={"code": "FORBIDDEN", "message": "No tienes permiso para esta acción."},
)


def _handle_write_errors(exc: Exception) -> None:
    if isinstance(exc, EmailAlreadyExistsError):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "EMAIL_ALREADY_EXISTS", "message": "El email ya está registrado."},
        ) from exc
    if isinstance(exc, BranchRequiredError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "BRANCH_REQUIRED",
                "message": "Este rol requiere una sucursal asignada.",
            },
        ) from exc
    if isinstance(exc, InsufficientPermissionsError):
        raise _FORBIDDEN from exc
    if isinstance(exc, RolInvalidoError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "ROL_INVALIDO", "message": "El rol indicado no existe o está inactivo."},
        ) from exc


@router.get("", response_model=list[UserResponse])
async def get_users(
    current_user: TokenData = Depends(require_permission("usuarios:listar")),
    conn: asyncpg.Connection = Depends(get_db),
) -> list[UserResponse]:
    return await list_users(conn, current_user)


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def post_user(
    body: UserCreateRequest,
    current_user: TokenData = Depends(require_permission("usuarios:crear")),
    conn: asyncpg.Connection = Depends(get_db),
) -> UserResponse:
    try:
        return await create_user(conn, body, current_user)
    except (
        EmailAlreadyExistsError,
        BranchRequiredError,
        InsufficientPermissionsError,
        RolInvalidoError,
    ) as exc:
        _handle_write_errors(exc)
        raise  # unreachable, satisfies mypy


@router.get("/{usuario_id}", response_model=UserResponse)
async def get_user_endpoint(
    usuario_id: UUID,
    current_user: TokenData = Depends(require_permission("usuarios:ver")),
    conn: asyncpg.Connection = Depends(get_db),
) -> UserResponse:
    try:
        return await get_user(conn, usuario_id, current_user)
    except UserNotFoundError:
        raise _NOT_FOUND from None
    except InsufficientPermissionsError:
        raise _FORBIDDEN from None


@router.put("/{usuario_id}", response_model=UserResponse)
async def put_user(
    usuario_id: UUID,
    body: UserUpdateRequest,
    current_user: TokenData = Depends(require_permission("usuarios:editar")),
    conn: asyncpg.Connection = Depends(get_db),
) -> UserResponse:
    try:
        return await update_user(conn, usuario_id, body, current_user)
    except UserNotFoundError:
        raise _NOT_FOUND from None
    except (
        EmailAlreadyExistsError,
        BranchRequiredError,
        InsufficientPermissionsError,
        RolInvalidoError,
    ) as exc:
        _handle_write_errors(exc)
        raise  # unreachable, satisfies mypy


@router.delete("/{usuario_id}")
async def delete_user_endpoint(
    usuario_id: UUID,
    current_user: TokenData = Depends(require_permission("usuarios:eliminar")),
    conn: asyncpg.Connection = Depends(get_db),
) -> Response:
    try:
        await delete_user(conn, usuario_id, current_user)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except UserNotFoundError:
        raise _NOT_FOUND from None
    except InsufficientPermissionsError:
        raise _FORBIDDEN from None
