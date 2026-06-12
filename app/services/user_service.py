from __future__ import annotations

from uuid import UUID

import asyncpg

from app.core.security import hash_password
from app.repositories.user_repository import (
    UsuarioRecord,
    assign_usuario_to_branch,
    create_usuario,
    delete_usuario,
    email_exists,
    get_all_usuarios,
    get_usuario_by_id,
    get_usuarios_by_branch,
    update_usuario,
    update_usuario_branch,
)
from app.schemas.auth import RoleEnum, TokenData
from app.schemas.user import UserCreateRequest, UserResponse, UserUpdateRequest


class EmailAlreadyExistsError(Exception):
    pass


class BranchRequiredError(Exception):
    pass


class InsufficientPermissionsError(Exception):
    pass


class UserNotFoundError(Exception):
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


def _assert_admin_scope(current_user: TokenData, target: UsuarioRecord) -> None:
    """Valida que un Administrador solo opere sobre usuarios de su sucursal."""
    if current_user.role == RoleEnum.administrador:
        if target["sucursal_id"] != current_user.branch_id:
            raise InsufficientPermissionsError
        if RoleEnum(target["rol"]) not in _roles_require_branch():
            raise InsufficientPermissionsError


async def list_users(conn: asyncpg.Connection, current_user: TokenData) -> list[UserResponse]:
    if current_user.role == RoleEnum.administrador_sistema:
        records = await get_all_usuarios(conn)
    else:
        if current_user.branch_id is None:
            return []
        records = await get_usuarios_by_branch(conn, current_user.branch_id)
    return [_to_response(r) for r in records]


async def get_user(
    conn: asyncpg.Connection, user_id: UUID, current_user: TokenData
) -> UserResponse:
    record = await get_usuario_by_id(conn, user_id)
    if record is None:
        raise UserNotFoundError
    _assert_admin_scope(current_user, record)
    return _to_response(record)


async def create_user(
    conn: asyncpg.Connection,
    data: UserCreateRequest,
    current_user: TokenData,
) -> UserResponse:
    if data.role == RoleEnum.administrador_sistema:
        raise InsufficientPermissionsError
    if current_user.role == RoleEnum.administrador:
        if data.role not in _roles_require_branch():
            raise InsufficientPermissionsError
        if data.branch_id != current_user.branch_id:
            raise InsufficientPermissionsError
    if data.role in _roles_require_branch() and data.branch_id is None:
        raise BranchRequiredError
    if await email_exists(conn, data.email):
        raise EmailAlreadyExistsError

    creator_id = UUID(current_user.sub)
    async with conn.transaction():
        user_id = await create_usuario(
            conn,
            email=data.email,
            password_hash=hash_password(data.password),
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


async def update_user(
    conn: asyncpg.Connection,
    user_id: UUID,
    data: UserUpdateRequest,
    current_user: TokenData,
) -> UserResponse:
    target = await get_usuario_by_id(conn, user_id)
    if target is None:
        raise UserNotFoundError

    # No se puede editar un AdministradorSistema por API
    if RoleEnum(target["rol"]) == RoleEnum.administrador_sistema:
        raise InsufficientPermissionsError

    _assert_admin_scope(current_user, target)

    if data.role == RoleEnum.administrador_sistema:
        raise InsufficientPermissionsError
    if current_user.role == RoleEnum.administrador:
        if data.role not in _roles_require_branch():
            raise InsufficientPermissionsError
        if data.branch_id != current_user.branch_id:
            raise InsufficientPermissionsError
    if data.role in _roles_require_branch() and data.branch_id is None:
        raise BranchRequiredError
    if data.email != target["email"] and await email_exists(conn, data.email):
        raise EmailAlreadyExistsError

    editor_id = UUID(current_user.sub)
    password_hash = hash_password(data.password) if data.password else None
    branch_changed = data.branch_id != target["sucursal_id"]

    async with conn.transaction():
        updated = await update_usuario(
            conn,
            user_id=user_id,
            email=data.email,
            nombre_completo=data.full_name,
            rol=data.role.value,
            password_hash=password_hash,
            modificado_por=editor_id,
        )
        if not updated:
            raise UserNotFoundError
        if branch_changed:
            await update_usuario_branch(conn, user_id, data.branch_id, editor_id)

    record = await get_usuario_by_id(conn, user_id)
    if record is None:
        raise UserNotFoundError
    return _to_response(record)


async def delete_user(conn: asyncpg.Connection, user_id: UUID, current_user: TokenData) -> None:
    target = await get_usuario_by_id(conn, user_id)
    if target is None:
        raise UserNotFoundError
    if RoleEnum(target["rol"]) == RoleEnum.administrador_sistema:
        raise InsufficientPermissionsError
    _assert_admin_scope(current_user, target)
    deleted = await delete_usuario(conn, user_id, UUID(current_user.sub))
    if not deleted:
        raise UserNotFoundError
