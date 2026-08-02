from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import asyncpg

from app.core.config import settings
from app.core.roles import ROL_ADMINISTRADOR, ROL_SISTEMA
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_refresh_token,
    verify_password,
)
from app.repositories.branch_repository import get_sucursal_nombre, get_sucursales_by_ids
from app.repositories.refresh_token_repository import (
    create_refresh_token,
    get_refresh_token,
    revoke_refresh_token,
)
from app.repositories.user_repository import (
    get_sucursal_ids_activas,
    get_usuario_by_email,
    get_usuario_by_id,
)
from app.schemas.auth import (
    BranchOption,
    BranchSelectionRequired,
    LoginResponse,
    UserOut,
)
from app.services.permission_service import get_permissions


class InvalidCredentialsError(Exception):
    pass


class SucursalNoAsignadaError(Exception):
    pass


class InvalidRefreshTokenError(Exception):
    pass


async def login(
    conn: asyncpg.Connection,
    email: str,
    password: str,
    sucursal_id: UUID | None,
    remember_me: bool,
) -> LoginResponse | BranchSelectionRequired:
    usuario = await get_usuario_by_email(conn, email)

    if usuario is None or not verify_password(password, usuario["password_hash"]):
        raise InvalidCredentialsError

    rol = usuario["rol"]
    permissions = get_permissions(rol)

    sucursal_efectiva: UUID | None = None
    if rol == ROL_ADMINISTRADOR:
        # Un Administrador puede tener varias sucursales via usuarios_sucursal
        # (a diferencia de Cajero/Cocina, que siguen siendo 1:1 más abajo).
        sucursales_activas = await get_sucursal_ids_activas(conn, usuario["id"])
        if not sucursales_activas:
            raise SucursalNoAsignadaError
        if len(sucursales_activas) == 1:
            sucursal_efectiva = sucursales_activas[0]
        elif sucursal_id is not None and sucursal_id in sucursales_activas:
            sucursal_efectiva = sucursal_id
        elif sucursal_id is not None:
            raise SucursalNoAsignadaError
        else:
            opciones = await get_sucursales_by_ids(conn, sucursales_activas)
            return BranchSelectionRequired(
                sucursales=[BranchOption(id=o["id"], nombre=o["nombre"]) for o in opciones]
            )
    elif rol != ROL_SISTEMA:
        sucursal_en_bd = usuario["sucursal_id"]
        if sucursal_en_bd is None:
            raise SucursalNoAsignadaError
        if sucursal_id is not None and sucursal_id != sucursal_en_bd:
            raise SucursalNoAsignadaError
        sucursal_efectiva = sucursal_en_bd

    access_minutes = (
        settings.access_token_remember_me_minutes
        if remember_me
        else settings.access_token_expire_minutes
    )
    refresh_days = (
        settings.refresh_token_remember_me_days
        if remember_me
        else settings.refresh_token_expire_days
    )

    token = create_access_token(
        payload={
            "sub": str(usuario["id"]),
            "email": usuario["email"],
            "role": rol,
            "branch_id": str(sucursal_efectiva) if sucursal_efectiva else None,
            "permissions": permissions,
        },
        expires_delta=timedelta(minutes=access_minutes),
    )

    raw_refresh, refresh_hash = generate_refresh_token()
    refresh_expires_at = datetime.now(UTC) + timedelta(days=refresh_days)
    await create_refresh_token(
        conn, usuario["id"], refresh_hash, refresh_expires_at, sucursal_efectiva
    )

    branch_name = await get_sucursal_nombre(conn, sucursal_efectiva) if sucursal_efectiva else None

    return LoginResponse(
        token=token,
        expires_in=access_minutes * 60,
        refresh_token=raw_refresh,
        refresh_expires_in=refresh_days * 86400,
        user=UserOut(
            id=usuario["id"],
            full_name=usuario["nombre_completo"],
            email=usuario["email"],
            role=rol,
            branch_id=sucursal_efectiva,
            branch_name=branch_name,
            permissions=permissions,
        ),
    )


async def refresh_access_token(
    conn: asyncpg.Connection,
    raw_refresh_token: str,
) -> LoginResponse:
    """Valida el refresh token, lo rota y emite un nuevo access token."""
    token_hash = hash_refresh_token(raw_refresh_token)
    record = await get_refresh_token(conn, token_hash)

    if record is None or record["revocado"] or record["expires_at"] < datetime.now(UTC):
        raise InvalidRefreshTokenError

    # Revocar el refresh token usado (rotación)
    await revoke_refresh_token(conn, token_hash)

    usuario = await get_usuario_by_id(conn, record["usuario_id"])
    if usuario is None or not usuario["activo"]:
        raise InvalidRefreshTokenError

    rol = usuario["rol"]
    if rol == ROL_SISTEMA:
        sucursal_efectiva: UUID | None = None
    elif rol == ROL_ADMINISTRADOR:
        # Un Administrador puede tener varias sucursales via usuarios_sucursal;
        # revalidamos que la guardada en el refresh token siga activa (pudo
        # habérsele quitado esa sucursal desde el login).
        sucursales_activas = await get_sucursal_ids_activas(conn, usuario["id"])
        if not sucursales_activas:
            raise InvalidRefreshTokenError
        sucursal_efectiva = record["sucursal_id"]
        if sucursal_efectiva not in sucursales_activas:
            sucursal_efectiva = sucursales_activas[0]
    else:
        # Cajero/Cocina siguen siendo 1:1 con una sola sucursal en el usuario.
        sucursal_efectiva = usuario["sucursal_id"]

    permissions = get_permissions(rol)

    token = create_access_token(
        payload={
            "sub": str(usuario["id"]),
            "email": usuario["email"],
            "role": rol,
            "branch_id": str(sucursal_efectiva) if sucursal_efectiva else None,
            "permissions": permissions,
        },
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
    )

    raw_new, new_hash = generate_refresh_token()
    refresh_expires_at = datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days)
    await create_refresh_token(conn, usuario["id"], new_hash, refresh_expires_at, sucursal_efectiva)

    branch_name = await get_sucursal_nombre(conn, sucursal_efectiva) if sucursal_efectiva else None

    return LoginResponse(
        token=token,
        expires_in=settings.access_token_expire_minutes * 60,
        refresh_token=raw_new,
        refresh_expires_in=settings.refresh_token_expire_days * 86400,
        user=UserOut(
            id=usuario["id"],
            full_name=usuario["nombre_completo"],
            email=usuario["email"],
            role=rol,
            branch_id=sucursal_efectiva,
            branch_name=branch_name,
            permissions=permissions,
        ),
    )
