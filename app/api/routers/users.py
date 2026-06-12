from __future__ import annotations

from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.api.deps import require_role
from app.core.database import get_db
from app.schemas.auth import RoleEnum, TokenData
from app.schemas.user import UserCreateRequest, UserResponse, UserUpdateRequest
from app.services.user_service import (
    BranchRequiredError,
    EmailAlreadyExistsError,
    InsufficientPermissionsError,
    UserNotFoundError,
    create_user,
    delete_user,
    get_user,
    list_users,
    update_user,
)

router = APIRouter(prefix="/api/users", tags=["users"])

_admin_roles = require_role(RoleEnum.administrador_sistema, RoleEnum.administrador)

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


@router.get("", response_model=list[UserResponse])
async def get_users(
    current_user: TokenData = Depends(_admin_roles),
    conn: asyncpg.Connection = Depends(get_db),
) -> list[UserResponse]:
    return await list_users(conn, current_user)


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def post_user(
    body: UserCreateRequest,
    current_user: TokenData = Depends(_admin_roles),
    conn: asyncpg.Connection = Depends(get_db),
) -> UserResponse:
    try:
        return await create_user(conn, body, current_user)
    except (EmailAlreadyExistsError, BranchRequiredError, InsufficientPermissionsError) as exc:
        _handle_write_errors(exc)
        raise  # unreachable, satisfies mypy


@router.get("/{user_id}", response_model=UserResponse)
async def get_user_endpoint(
    user_id: UUID,
    current_user: TokenData = Depends(_admin_roles),
    conn: asyncpg.Connection = Depends(get_db),
) -> UserResponse:
    try:
        return await get_user(conn, user_id, current_user)
    except UserNotFoundError:
        raise _NOT_FOUND from None
    except InsufficientPermissionsError:
        raise _FORBIDDEN from None


@router.put("/{user_id}", response_model=UserResponse)
async def put_user(
    user_id: UUID,
    body: UserUpdateRequest,
    current_user: TokenData = Depends(_admin_roles),
    conn: asyncpg.Connection = Depends(get_db),
) -> UserResponse:
    try:
        return await update_user(conn, user_id, body, current_user)
    except UserNotFoundError:
        raise _NOT_FOUND from None
    except (EmailAlreadyExistsError, BranchRequiredError, InsufficientPermissionsError) as exc:
        _handle_write_errors(exc)
        raise  # unreachable, satisfies mypy


@router.delete("/{user_id}")
async def delete_user_endpoint(
    user_id: UUID,
    current_user: TokenData = Depends(_admin_roles),
    conn: asyncpg.Connection = Depends(get_db),
) -> Response:
    try:
        await delete_user(conn, user_id, current_user)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except UserNotFoundError:
        raise _NOT_FOUND from None
    except InsufficientPermissionsError:
        raise _FORBIDDEN from None
