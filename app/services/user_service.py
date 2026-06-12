from __future__ import annotations

from uuid import UUID

import asyncpg

from app.core.security import hash_password
from app.repositories.user_repository import (
    UsuarioRecord,
    assign_usuario_to_branch,
    create_usuario,
    email_exists,
    get_all_usuarios,
    get_usuario_by_id,
    get_usuarios_by_branch,
)
from app.schemas.auth import RoleEnum, TokenData
from app.schemas.user import UserCreateRequest, UserResponse


class EmailAlreadyExistsError(Exception):
    pass


class BranchRequiredError(Exception):
    pass


class InsufficientPermissionsError(Exception):
    pass


def _roles_require_branch() -> tuple[RoleEnum, ...]:
    return (RoleEnum.cajero, RoleEnum.cocina)


def _to_response(record: UsuarioRecord) -> UserResponse:
    return UserResponse(
        id=record["id"],
        full_name=record["nombre_completo"],
        email=record["email"],
        role=RoleEnum(record["rol"]),
        branch_id=record["sucursal_id"],
        is_active=record["activo"],
    )


async def list_users(conn: asyncpg.Connection, current_user: TokenData) -> list[UserResponse]:
    if current_user.role == RoleEnum.administrador_sistema:
        records = await get_all_usuarios(conn)
    else:
        if current_user.branch_id is None:
            return []
        records = await get_usuarios_by_branch(conn, current_user.branch_id)
    return [_to_response(r) for r in records]


async def create_user(
    conn: asyncpg.Connection,
    data: UserCreateRequest,
    current_user: TokenData,
) -> UserResponse:
    # AdministradorSistema no se crea por API
    if data.role == RoleEnum.administrador_sistema:
        raise InsufficientPermissionsError

    # Administrador solo puede crear Cajero/Cocina en su propia sucursal
    if current_user.role == RoleEnum.administrador:
        if data.role not in _roles_require_branch():
            raise InsufficientPermissionsError
        if data.branch_id != current_user.branch_id:
            raise InsufficientPermissionsError

    # Cajero/Cocina requieren sucursal
    if data.role in _roles_require_branch() and data.branch_id is None:
        raise BranchRequiredError

    if await email_exists(conn, data.email):
        raise EmailAlreadyExistsError

    creator_id = UUID(current_user.sub)
    password_hash = hash_password(data.password)

    async with conn.transaction():
        user_id = await create_usuario(
            conn,
            email=data.email,
            password_hash=password_hash,
            nombre_completo=data.full_name,
            rol=data.role.value,
            creado_por=creator_id,
        )
        if data.branch_id is not None:
            await assign_usuario_to_branch(conn, user_id, data.branch_id, creator_id)

    record = await get_usuario_by_id(conn, user_id)
    if record is None:
        raise RuntimeError("Error al recuperar el usuario recién creado")
    return _to_response(record)
