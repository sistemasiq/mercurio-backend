from __future__ import annotations

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.security import hash_refresh_token
from app.repositories.refresh_token_repository import revoke_refresh_token
from app.repositories.token_repository import revoke_token
from app.repositories.user_repository import get_usuario_by_id
from app.schemas.auth import (
    BranchSelectionRequired,
    LoginRequest,
    LoginResponse,
    RefreshRequest,
    TokenData,
    UserOut,
)
from app.services.auth_service import (
    InvalidCredentialsError,
    InvalidRefreshTokenError,
    SucursalNoAsignadaError,
    login,
    refresh_access_token,
)
from app.services.permission_service import get_permissions

router = APIRouter(prefix="/api/auth", tags=["Autenticación"])

_INVALID_CREDENTIALS = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail={"code": "INVALID_CREDENTIALS", "message": "Credenciales incorrectas."},
)
_INVALID_REFRESH = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail={"code": "TOKEN_INVALID", "message": "Refresh token inválido o expirado."},
)


@router.post("/login", response_model=LoginResponse | BranchSelectionRequired)
async def login_endpoint(
    body: LoginRequest,
    conn: asyncpg.Connection = Depends(get_db),
) -> LoginResponse | BranchSelectionRequired:
    try:
        return await login(
            conn=conn,
            email=body.email,
            password=body.password,
            sucursal_id=body.sucursal_id,
            remember_me=body.remember_me,
        )
    except (InvalidCredentialsError, SucursalNoAsignadaError):
        raise _INVALID_CREDENTIALS from None


@router.get("/me", response_model=UserOut)
async def me_endpoint(
    current_user: TokenData = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db),
) -> UserOut:
    """Devuelve los datos actuales del usuario autenticado desde la BD."""
    from uuid import UUID

    usuario = await get_usuario_by_id(conn, UUID(current_user.sub))
    if usuario is None or not usuario["activo"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "USER_NOT_FOUND", "message": "Usuario no encontrado o inactivo."},
        )
    rol = usuario["rol"]
    return UserOut(
        id=usuario["id"],
        full_name=usuario["nombre_completo"],
        email=usuario["email"],
        role=rol,
        branch_id=current_user.branch_id,
        permissions=get_permissions(rol),
    )


@router.post("/refresh", response_model=LoginResponse)
async def refresh_endpoint(
    body: RefreshRequest,
    conn: asyncpg.Connection = Depends(get_db),
) -> LoginResponse:
    """Rota el refresh token y emite un nuevo access token."""
    try:
        return await refresh_access_token(conn, body.refresh_token)
    except InvalidRefreshTokenError:
        raise _INVALID_REFRESH from None


@router.post("/logout")
async def logout_endpoint(
    body: RefreshRequest,
    current_user: TokenData = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db),
) -> Response:
    """Revoca el access token (blacklist) y el refresh token."""
    await revoke_token(conn, current_user.jti, current_user.exp)
    await revoke_refresh_token(conn, hash_refresh_token(body.refresh_token))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
