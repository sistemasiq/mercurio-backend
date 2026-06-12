from __future__ import annotations

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import require_role
from app.core.database import get_db
from app.schemas.auth import RoleEnum, TokenData
from app.schemas.user import UserCreateRequest, UserResponse
from app.services.user_service import (
    BranchRequiredError,
    EmailAlreadyExistsError,
    InsufficientPermissionsError,
    create_user,
    list_users,
)

router = APIRouter(prefix="/api/users", tags=["users"])

_admin_roles = require_role(RoleEnum.administrador_sistema, RoleEnum.administrador)


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
    except EmailAlreadyExistsError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "EMAIL_ALREADY_EXISTS", "message": "El email ya está registrado."},
        ) from None
    except BranchRequiredError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "BRANCH_REQUIRED",
                "message": "Este rol requiere una sucursal asignada.",
            },
        ) from None
    except InsufficientPermissionsError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "FORBIDDEN",
                "message": "No tienes permiso para crear este tipo de usuario.",
            },
        ) from None
