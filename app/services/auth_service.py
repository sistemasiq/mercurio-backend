from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import asyncpg

from app.core.config import settings
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_refresh_token,
    verify_password,
)
from app.repositories.refresh_token_repository import (
    create_refresh_token,
    get_refresh_token,
    revoke_refresh_token,
)
from app.repositories.user_repository import get_usuario_by_email, get_usuario_by_id
from app.schemas.auth import LoginResponse, RoleEnum, UserOut
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
) -> LoginResponse:
    usuario = await get_usuario_by_email(conn, email)

    if usuario is None or not verify_password(password, usuario["password_hash"]):
        raise InvalidCredentialsError

    rol = RoleEnum(usuario["rol"])
    permissions = get_permissions(rol.value)

    sucursal_efectiva: UUID | None = None
    if rol != RoleEnum.administrador_sistema:
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
            "role": rol.value,
            "branch_id": str(sucursal_efectiva) if sucursal_efectiva else None,
            "permissions": permissions,
        },
        expires_delta=timedelta(minutes=access_minutes),
    )

    raw_refresh, refresh_hash = generate_refresh_token()
    refresh_expires_at = datetime.now(UTC) + timedelta(days=refresh_days)
    await create_refresh_token(conn, usuario["id"], refresh_hash, refresh_expires_at)

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

    rol = RoleEnum(usuario["rol"])
    sucursal_efectiva: UUID | None = usuario["sucursal_id"]
    permissions = get_permissions(rol.value)

    token = create_access_token(
        payload={
            "sub": str(usuario["id"]),
            "email": usuario["email"],
            "role": rol.value,
            "branch_id": str(sucursal_efectiva) if sucursal_efectiva else None,
            "permissions": permissions,
        },
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
    )

    raw_new, new_hash = generate_refresh_token()
    refresh_expires_at = datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days)
    await create_refresh_token(conn, usuario["id"], new_hash, refresh_expires_at)

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
            permissions=permissions,
        ),
    )
