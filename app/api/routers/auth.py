from __future__ import annotations

from datetime import UTC, datetime, timedelta

import asyncpg
from fastapi import APIRouter, Body, Cookie, Depends, HTTPException, Response, status

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.core.security import generate_ws_ticket, hash_refresh_token
from app.repositories.branch_repository import get_sucursal_nombre
from app.repositories.refresh_token_repository import revoke_refresh_token
from app.repositories.token_repository import revoke_token
from app.repositories.user_repository import get_usuario_by_id
from app.repositories.ws_ticket_repository import create_ws_ticket
from app.schemas.auth import (
    BranchSelectionRequired,
    LoginRequest,
    LoginResponse,
    RefreshRequest,
    TokenData,
    UserOut,
    WsTicketResponse,
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

_REFRESH_COOKIE_NAME = "refresh_token"
_REFRESH_COOKIE_PATH = "/api/auth"

_INVALID_CREDENTIALS = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail={"code": "INVALID_CREDENTIALS", "message": "Credenciales incorrectas."},
)
_NO_BRANCH_ASSIGNED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail={
        "code": "NO_BRANCH_ASSIGNED",
        "message": (
            "Tu cuenta no tiene ninguna sucursal asignada. "
            "Contacta a un administrador del sistema."
        ),
    },
)
_INVALID_REFRESH = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail={"code": "TOKEN_INVALID", "message": "Refresh token inválido o expirado."},
)


def _set_refresh_cookie(response: Response, raw_refresh_token: str, max_age_seconds: int) -> None:
    """QA #32 — además del body (ver settings.refresh_en_body), el refresh
    token viaja en una cookie HttpOnly restringida a /api/auth para que un XSS
    no pueda leerlo desde JS."""
    response.set_cookie(
        key=_REFRESH_COOKIE_NAME,
        value=raw_refresh_token,
        max_age=max_age_seconds,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="strict",
        path=_REFRESH_COOKIE_PATH,
    )


def _apply_cookie_policy(response: Response, result: LoginResponse) -> LoginResponse:
    _set_refresh_cookie(response, result.refresh_token, result.refresh_expires_in)
    if not settings.refresh_en_body:
        return result.model_copy(update={"refresh_token": ""})
    return result


@router.post("/login", response_model=LoginResponse | BranchSelectionRequired)
async def login_endpoint(
    body: LoginRequest,
    response: Response,
    conn: asyncpg.Connection = Depends(get_db),
) -> LoginResponse | BranchSelectionRequired:
    try:
        result = await login(
            conn=conn,
            email=body.email,
            password=body.password,
            sucursal_id=body.sucursal_id,
            remember_me=body.remember_me,
        )
    except InvalidCredentialsError:
        raise _INVALID_CREDENTIALS from None
    except SucursalNoAsignadaError:
        raise _NO_BRANCH_ASSIGNED from None

    if isinstance(result, LoginResponse):
        return _apply_cookie_policy(response, result)
    return result


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
    branch_name = (
        await get_sucursal_nombre(conn, current_user.branch_id) if current_user.branch_id else None
    )
    return UserOut(
        id=usuario["id"],
        full_name=usuario["nombre_completo"],
        email=usuario["email"],
        role=rol,
        branch_id=current_user.branch_id,
        branch_name=branch_name,
        permissions=get_permissions(rol),
        tiene_pin=bool(usuario["pin_hash"]),
    )


@router.post("/refresh", response_model=LoginResponse)
async def refresh_endpoint(
    response: Response,
    body: RefreshRequest | None = Body(None),
    refresh_token_cookie: str | None = Cookie(None, alias=_REFRESH_COOKIE_NAME),
    conn: asyncpg.Connection = Depends(get_db),
) -> LoginResponse:
    """Rota el refresh token y emite un nuevo access token. Acepta el refresh
    token desde la cookie HttpOnly o, si no vino, desde el body (QA #32:
    clientes viejos que todavía no mandan cookies)."""
    raw_token = refresh_token_cookie or (body.refresh_token if body else None)
    if not raw_token:
        raise _INVALID_REFRESH
    try:
        result = await refresh_access_token(conn, raw_token)
    except InvalidRefreshTokenError:
        raise _INVALID_REFRESH from None

    return _apply_cookie_policy(response, result)


@router.post("/logout")
async def logout_endpoint(
    response: Response,
    current_user: TokenData = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db),
    body: RefreshRequest | None = Body(None),
    refresh_token_cookie: str | None = Cookie(None, alias=_REFRESH_COOKIE_NAME),
) -> Response:
    """Revoca el access token (blacklist) y el refresh token (cookie o body,
    QA #32) y borra la cookie."""
    raw_token = refresh_token_cookie or (body.refresh_token if body else None)
    await revoke_token(conn, current_user.jti, current_user.exp)
    if raw_token:
        await revoke_refresh_token(conn, hash_refresh_token(raw_token))
    response.delete_cookie(key=_REFRESH_COOKIE_NAME, path=_REFRESH_COOKIE_PATH)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/ws-ticket", response_model=WsTicketResponse)
async def ws_ticket_endpoint(
    current_user: TokenData = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db),
) -> WsTicketResponse:
    """QA #32 — emite un ticket aleatorio de un solo uso (30 s) para que los
    WebSockets de comandas/estancias no necesiten el JWT crudo en la URL."""
    raw_ticket, ticket_hash = generate_ws_ticket()
    claims = {
        "sub": current_user.sub,
        "email": current_user.email,
        "role": current_user.role,
        "branch_id": str(current_user.branch_id) if current_user.branch_id else None,
        "permissions": current_user.permissions,
        "jti": current_user.jti,
        "exp": current_user.exp.isoformat(),
    }
    expires_at = datetime.now(UTC) + timedelta(seconds=settings.ws_ticket_ttl_seconds)
    await create_ws_ticket(conn, ticket_hash, claims, expires_at)
    return WsTicketResponse(ticket=raw_ticket, expires_in=settings.ws_ticket_ttl_seconds)
