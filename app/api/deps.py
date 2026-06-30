from collections.abc import Awaitable, Callable

import asyncpg
from fastapi import Depends, Header

from app.core.database import get_db
from app.core.security import JWTError, decodificar_token
from app.exceptions import CredencialesInvalidas, SinPermiso
from app.repositories import tokens_revocados
from app.schemas.auth import TokenData


async def get_current_user(
    authorization: str | None = Header(default=None),
    conn: asyncpg.Connection = Depends(get_db),
) -> TokenData:
    """Valida el Bearer JWT, comprueba el jti contra la blacklist y devuelve TokenData."""
    if not authorization or not authorization.lower().startswith("bearer"):
        raise CredencialesInvalidas()
    token = authorization[len("bearer") :].strip()
    try:
        payload = decodificar_token(token)
        datos = TokenData(
            sub=payload["sub"],
            email=payload["email"],
            role=payload["role"],
            branch_id=payload.get("branch_id"),
            jti=payload["jti"],
        )
    except (JWTError, KeyError, ValueError):
        raise CredencialesInvalidas() from None

    if await tokens_revocados.esta_revocado(conn, datos.jti):
        raise CredencialesInvalidas()
    return datos


def require_role(
    *roles: str,
) -> Callable[[TokenData], Awaitable[TokenData]]:
    """Dependencia que exige que el usuario tenga uno de los roles indicados."""

    async def checker(user: TokenData = Depends(get_current_user)) -> TokenData:
        if user.role not in roles:
            raise SinPermiso()
        return user

    return checker
