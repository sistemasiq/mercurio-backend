from __future__ import annotations

from datetime import timedelta
from uuid import UUID

import asyncpg

from app.core.config import settings
from app.core.security import create_access_token, verify_password
from app.repositories.user_repository import get_usuario_by_email
from app.schemas.auth import LoginResponse, RoleEnum, UserOut


class InvalidCredentialsError(Exception):
    pass


class SucursalNoAsignadaError(Exception):
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

    # AdministradorSistema: sin sucursal.
    # Otros roles: usar la sucursal del request si se envía, o la asignada en BD.
    # Si se envía y no coincide con la asignada → acceso denegado.
    sucursal_efectiva: UUID | None = None
    if rol != RoleEnum.administrador_sistema:
        sucursal_en_bd = usuario["sucursal_id"]
        if sucursal_en_bd is None:
            raise SucursalNoAsignadaError
        if sucursal_id is not None and sucursal_id != sucursal_en_bd:
            raise SucursalNoAsignadaError
        sucursal_efectiva = sucursal_en_bd

    expires_minutes = (
        settings.access_token_remember_me_minutes
        if remember_me
        else settings.access_token_expire_minutes
    )

    token = create_access_token(
        payload={
            "sub": str(usuario["id"]),
            "email": usuario["email"],
            "role": rol.value,
            "branch_id": str(sucursal_efectiva) if sucursal_efectiva else None,
        },
        expires_delta=timedelta(minutes=expires_minutes),
    )

    return LoginResponse(
        token=token,
        expires_in=expires_minutes * 60,
        user=UserOut(
            id=usuario["id"],
            full_name=usuario["nombre_completo"],
            email=usuario["email"],
            role=rol,
            branch_id=sucursal_efectiva,
        ),
    )
