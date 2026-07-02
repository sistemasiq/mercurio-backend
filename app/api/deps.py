from collections.abc import Callable, Coroutine
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import asyncpg
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError

from app.core.database import get_db
from app.core.security import decode_access_token
from app.repositories.token_repository import is_token_revoked
from app.schemas.auth import RoleEnum, TokenData

_bearer = HTTPBearer()

_FORBIDDEN = HTTPException(
    status_code=status.HTTP_403_FORBIDDEN,
    detail={"code": "FORBIDDEN", "message": "No tienes permiso para realizar esta acción."},
)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    conn: asyncpg.Connection = Depends(get_db),
) -> TokenData:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"code": "INVALID_TOKEN", "message": "Token inválido o expirado."},
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(credentials.credentials)
        sub = payload.get("sub")
        email = payload.get("email")
        role = payload.get("role")
        branch_id = payload.get("branch_id")
        permissions = payload.get("permissions")
        jti = payload.get("jti")
        exp = payload.get("exp")

        if not isinstance(sub, str) or not isinstance(email, str) or not isinstance(jti, str):
            raise credentials_exception from None

        if await is_token_revoked(conn, jti):
            raise credentials_exception from None

        exp_dt = datetime.fromtimestamp(float(exp), tz=UTC) if exp is not None else None  # type: ignore[arg-type]

        return TokenData(
            sub=sub,
            email=email,
            role=RoleEnum(role),
            branch_id=UUID(branch_id) if isinstance(branch_id, str) else None,
            permissions=permissions if isinstance(permissions, list) else [],
            jti=jti,
            exp=exp_dt or datetime.now(tz=UTC),
        )
    except (JWTError, ValueError, KeyError):
        raise credentials_exception from None


def require_role(
    *allowed_roles: RoleEnum,
) -> Callable[..., Coroutine[Any, Any, TokenData]]:
    """Restringe el acceso a los roles indicados (comprobación por nombre de rol)."""

    async def dependency(
        current_user: TokenData = Depends(get_current_user),
    ) -> TokenData:
        if current_user.role not in allowed_roles:
            raise _FORBIDDEN
        return current_user

    return dependency


def require_permission(
    *codes: str,
) -> Callable[..., Coroutine[Any, Any, TokenData]]:
    """Restringe el acceso a usuarios cuyo rol tenga TODOS los permisos indicados."""
    from app.services.permission_service import has_permission

    async def dependency(
        current_user: TokenData = Depends(get_current_user),
    ) -> TokenData:
        if not all(has_permission(current_user.role.value, code) for code in codes):
            raise _FORBIDDEN
        return current_user

    return dependency
