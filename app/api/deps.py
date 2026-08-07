from collections.abc import Callable, Coroutine
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import asyncpg
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError

from app.core.database import get_db
from app.core.roles import ROL_SISTEMA
from app.core.security import decode_access_token
from app.repositories.token_repository import is_token_revoked
from app.schemas.auth import TokenData

_bearer = HTTPBearer()

_FORBIDDEN = HTTPException(
    status_code=status.HTTP_403_FORBIDDEN,
    detail={"code": "FORBIDDEN", "message": "No tienes permiso para realizar esta acción."},
)


_INVALID_TOKEN = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail={"code": "INVALID_TOKEN", "message": "Token inválido o expirado."},
    headers={"WWW-Authenticate": "Bearer"},
)

_SERVICE_UNAVAILABLE = HTTPException(
    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
    detail={
        "code": "SERVICE_UNAVAILABLE",
        "message": "No se pudo verificar la sesión porque la base de datos no respondió. Intenta de nuevo en unos segundos.",
    },
)


async def _resolve_token_data(token: str, conn: asyncpg.Connection) -> TokenData:
    """Decodifica y valida un JWT crudo. Compartido por auth vía header (HTTP) y
    vía query param (WebSocket, que no soporta headers custom en el handshake)."""
    try:
        payload = decode_access_token(token)
        sub = payload.get("sub")
        email = payload.get("email")
        role = payload.get("role")
        branch_id = payload.get("branch_id")
        permissions = payload.get("permissions")
        jti = payload.get("jti")
        exp = payload.get("exp")

        if (
            not isinstance(sub, str)
            or not isinstance(email, str)
            or not isinstance(jti, str)
            or not isinstance(role, str)
        ):
            raise _INVALID_TOKEN from None

        # Una caída/latencia de la conexión a BD (ej. Tailscale) no es lo mismo que un
        # token inválido — antes ambos casos se reportaban igual como 401, lo cual
        # confundía al usuario haciéndolo pensar en un problema de validación de datos.
        try:
            revocado = await is_token_revoked(conn, jti)
        except (asyncpg.PostgresError, OSError) as exc:
            raise _SERVICE_UNAVAILABLE from exc

        if revocado:
            raise _INVALID_TOKEN from None

        exp_dt = datetime.fromtimestamp(float(exp), tz=UTC) if exp is not None else None  # type: ignore[arg-type]

        return TokenData(
            sub=sub,
            email=email,
            role=role,
            branch_id=UUID(branch_id) if isinstance(branch_id, str) else None,
            permissions=permissions if isinstance(permissions, list) else [],
            jti=jti,
            exp=exp_dt or datetime.now(tz=UTC),
        )
    except (JWTError, ValueError, KeyError):
        raise _INVALID_TOKEN from None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    conn: asyncpg.Connection = Depends(get_db),
    sucursal_vista: str | None = Header(None, alias="X-Sucursal-Vista"),
) -> TokenData:
    current_user = await _resolve_token_data(credentials.credentials, conn)
    # AdministradorSistema no tiene sucursal propia; este header opcional le
    # permite "pararse" en una sucursal para ver sus catálogos/listados como
    # los vería esa sucursal, sin necesidad de reautenticarse. Cualquier otro
    # rol lo ignora -- su branch_id siempre sale del token, nunca del cliente.
    if current_user.role == ROL_SISTEMA and sucursal_vista:
        try:
            current_user = current_user.model_copy(update={"branch_id": UUID(sucursal_vista)})
        except ValueError:
            pass
    return current_user


async def get_current_user_ws(token: str, conn: asyncpg.Connection) -> TokenData:
    """Igual que get_current_user, pero para el handshake de un WebSocket: el
    token llega por query param (?token=...) en vez de header Authorization,
    porque el navegador no permite headers custom en la conexión WS nativa."""
    return await _resolve_token_data(token, conn)


def require_role(
    *allowed_roles: str,
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
        if not all(has_permission(current_user.role, code) for code in codes):
            raise _FORBIDDEN
        return current_user

    return dependency


async def requiere_turno_abierto(
    current_user: TokenData = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db),
) -> TokenData:
    """RN-APE-005 / RN-CIE-001: sin un turno de caja en estado OPERANDO (ABIERTA),
    no se permite ninguna venta, cobro o pago — ni sin apertura, ni durante el
    conteo/cierre. Usar como dependencia extra en cualquier endpoint que registre
    una transacción monetaria (comandas, pagos de estancia/reservación, extras)."""
    from app.services.turnos_caja_service import verificar_turno_abierto

    await verificar_turno_abierto(conn, current_user.sub)
    return current_user


async def apertura_operando_id(
    current_user: TokenData = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db),
) -> str:
    """Igual que requiere_turno_abierto, pero además devuelve el id de la apertura
    activa — para endpoints que deben registrar el movimiento de venta/cobro
    correspondiente en movimientos_caja."""
    from app.services.turnos_caja_service import obtener_apertura_operando_id

    return await obtener_apertura_operando_id(conn, current_user.sub)
