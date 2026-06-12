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

    # AdministradorSistema no requiere sucursal; los demás roles sí.
    if rol != RoleEnum.administrador_sistema:
        if sucursal_id is None:
            raise SucursalNoAsignadaError
        if usuario["sucursal_id"] != sucursal_id:
            raise SucursalNoAsignadaError

    sucursal_efectiva = None if rol == RoleEnum.administrador_sistema else sucursal_id

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
