from __future__ import annotations

from uuid import UUID

import asyncpg

from app.core.roles import ROL_ADMINISTRADOR, ROL_SISTEMA, ROLES_SIN_SUCURSAL_FIJA
from app.core.security import hash_password
from app.repositories.permission_repository import get_rol_by_nombre
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
from app.schemas.auth import TokenData
from app.schemas.user import UserCreateRequest, UserResponse, UserUpdateRequest


class EmailAlreadyExistsError(Exception):
    pass


class BranchRequiredError(Exception):
    pass


class InsufficientPermissionsError(Exception):
    pass


class UserNotFoundError(Exception):
    pass


class RolInvalidoError(Exception):
    pass


def _role_requires_branch(role: str) -> bool:
    return role not in ROLES_SIN_SUCURSAL_FIJA


async def _assert_role_valid(conn: asyncpg.Connection, role: str) -> None:
    """Valida que el rol exista y esté activo (los roles ya no son un enum
    cerrado: se crean/desactivan desde el Catálogo de Roles)."""
    rol = await get_rol_by_nombre(conn, role)
    if rol is None or not rol["activo"]:
        raise RolInvalidoError


def _to_response(record: UsuarioRecord) -> UserResponse:
    return UserResponse(
        id=record["id"],
        full_name=record["nombre_completo"],
        email=record["email"],
        role=record["rol"],
        branch_id=record["sucursal_id"],
        is_active=record["activo"],
    )


def _assert_admin_scope(current_user: TokenData, target: UsuarioRecord) -> None:
    """Valida que un Administrador solo opere sobre usuarios de su sucursal."""
    if current_user.role == ROL_ADMINISTRADOR:
        if target["sucursal_id"] != current_user.branch_id:
            raise InsufficientPermissionsError
        if not _role_requires_branch(target["rol"]):
            raise InsufficientPermissionsError


async def list_users(conn: asyncpg.Connection, current_user: TokenData) -> list[UserResponse]:
    if current_user.branch_id is not None:
        records = await get_usuarios_by_branch(conn, current_user.branch_id)
    elif current_user.role == ROL_SISTEMA:
        records = await get_all_usuarios(conn)
    else:
        return []
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
    if data.role == ROL_SISTEMA:
        raise InsufficientPermissionsError
    await _assert_role_valid(conn, data.role)
    if current_user.role == ROL_ADMINISTRADOR:
        if not _role_requires_branch(data.role):
            raise InsufficientPermissionsError
        if data.branch_id != current_user.branch_id:
            raise InsufficientPermissionsError
    if _role_requires_branch(data.role) and data.branch_id is None:
        raise BranchRequiredError
    if await email_exists(conn, data.email):
        raise EmailAlreadyExistsError

    # Un Administrador se asigna a sucursales desde branch_service (puede
    # tener varias); branch_id aquí solo aplica a roles operativos.
    branch_id = data.branch_id if data.role != ROL_ADMINISTRADOR else None

    creator_id = UUID(current_user.sub)
    async with conn.transaction():
        user_id = await create_usuario(
            conn,
            email=data.email,
            password_hash=hash_password(data.password),
            nombre_completo=data.full_name,
            rol=data.role,
            creado_por=creator_id,
        )
        if branch_id is not None:
            await assign_usuario_to_branch(conn, user_id, branch_id, creator_id)

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
    if target["rol"] == ROL_SISTEMA:
        raise InsufficientPermissionsError

    _assert_admin_scope(current_user, target)

    if data.role == ROL_SISTEMA:
        raise InsufficientPermissionsError
    await _assert_role_valid(conn, data.role)
    if current_user.role == ROL_ADMINISTRADOR:
        if not _role_requires_branch(data.role):
            raise InsufficientPermissionsError
        if data.branch_id != current_user.branch_id:
            raise InsufficientPermissionsError
    if _role_requires_branch(data.role) and data.branch_id is None:
        raise BranchRequiredError
    if data.email != target["email"] and await email_exists(conn, data.email):
        raise EmailAlreadyExistsError

    editor_id = UUID(current_user.sub)
    password_hash = hash_password(data.password) if data.password else None
    # Un Administrador se reasigna a sucursales desde branch_service (puede
    # tener varias); este endpoint nunca debe tocar usuarios_sucursal para
    # ese rol, para no desactivar asignaciones hechas por ese otro camino.
    branch_id = data.branch_id if data.role != ROL_ADMINISTRADOR else None
    branch_changed = data.role != ROL_ADMINISTRADOR and branch_id != target["sucursal_id"]

    async with conn.transaction():
        updated = await update_usuario(
            conn,
            user_id=user_id,
            email=data.email,
            nombre_completo=data.full_name,
            rol=data.role,
            password_hash=password_hash,
            modificado_por=editor_id,
        )
        if not updated:
            raise UserNotFoundError
        if branch_changed:
            await update_usuario_branch(conn, user_id, branch_id, editor_id)

    record = await get_usuario_by_id(conn, user_id)
    if record is None:
        raise UserNotFoundError
    return _to_response(record)


async def delete_user(conn: asyncpg.Connection, user_id: UUID, current_user: TokenData) -> None:
    target = await get_usuario_by_id(conn, user_id)
    if target is None:
        raise UserNotFoundError
    if target["rol"] == ROL_SISTEMA:
        raise InsufficientPermissionsError
    _assert_admin_scope(current_user, target)
    deleted = await delete_usuario(conn, user_id, UUID(current_user.sub))
    if not deleted:
        raise UserNotFoundError
