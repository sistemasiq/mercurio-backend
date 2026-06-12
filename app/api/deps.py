from collections.abc import Callable, Coroutine
from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError

from app.core.security import decode_access_token
from app.schemas.auth import RoleEnum, TokenData

_bearer = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
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
        if not isinstance(sub, str) or not isinstance(email, str):
            raise credentials_exception from None
        return TokenData(
            sub=sub,
            email=email,
            role=RoleEnum(role),
            branch_id=branch_id,
        )
    except (JWTError, ValueError, KeyError):
        raise credentials_exception from None


def require_role(
    *allowed_roles: RoleEnum,
) -> Callable[..., Coroutine[Any, Any, TokenData]]:
    """Dependencia de FastAPI que restringe el acceso a los roles indicados."""

    async def dependency(
        current_user: TokenData = Depends(get_current_user),
    ) -> TokenData:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "FORBIDDEN",
                    "message": "No tienes permiso para realizar esta acción.",
                },
            )
        return current_user

    return dependency
