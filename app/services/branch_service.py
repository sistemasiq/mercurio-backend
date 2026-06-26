from __future__ import annotations

from uuid import UUID

import asyncpg

from app.repositories.branch_repository import (
    SucursalRecord,
    create_sucursal,
    deactivate_sucursal,
    get_all_sucursales,
    get_sucursal_by_id,
    nombre_exists,
    update_sucursal,
    reactivate_sucursal,
)
from app.schemas.auth import RoleEnum, TokenData
from app.schemas.branch import BranchCreateRequest, BranchResponse, BranchUpdateRequest


class NombreAlreadyExistsError(Exception):
    pass


class BranchNotFoundError(Exception):
    pass


class InsufficientPermissionsError(Exception):
    pass


def _to_response(record: SucursalRecord) -> BranchResponse:
    return BranchResponse(
        id=record["id"],
        nombre=record["nombre"],
        direccion=record["direccion"],
        telefono=record["telefono"],
        correo=record["correo"],
        administrador_id=record["administrador_id"],
        administrador_name=record["administrador_name"],
        clave=record["clave"],
        is_active=record["activo"],
        creado=record["creado"],
    )


async def list_branches(conn: asyncpg.Connection, current_user: TokenData) -> list[BranchResponse]:
    if current_user.role == RoleEnum.administrador_sistema:
        records = await get_all_sucursales(conn)
        return [_to_response(r) for r in records]
    if current_user.branch_id is None:
        return []
    record = await get_sucursal_by_id(conn, current_user.branch_id)
    return [_to_response(record)] if record else []


async def get_branch(
    conn: asyncpg.Connection, branch_id: UUID, current_user: TokenData
) -> BranchResponse:
    if current_user.role == RoleEnum.administrador and current_user.branch_id != branch_id:
        raise InsufficientPermissionsError
    record = await get_sucursal_by_id(conn, branch_id)
    if record is None:
        raise BranchNotFoundError
    return _to_response(record)


async def create_branch(
    conn: asyncpg.Connection,
    data: BranchCreateRequest,
    current_user: TokenData,
) -> BranchResponse:
    if await nombre_exists(conn, data.nombre):
        raise NombreAlreadyExistsError
    sucursal_id = await create_sucursal(
        conn,
        nombre=data.nombre,
        direccion=data.direccion,
        telefono=data.telefono,
        correo=data.correo,
        administrador_id=data.administrador_id,
        administrador_name=data.administrador_name,
        clave=data.clave,
        creado_por=UUID(current_user.sub),
    )
    record = await get_sucursal_by_id(conn, sucursal_id)
    if record is None:
        raise RuntimeError("Error al recuperar la sucursal recién creada")
    return _to_response(record)


async def update_branch(
    conn: asyncpg.Connection,
    branch_id: UUID,
    data: BranchUpdateRequest,
    current_user: TokenData,
) -> BranchResponse:
    record = await get_sucursal_by_id(conn, branch_id)
    if record is None:
        raise BranchNotFoundError
    if data.nombre != record["nombre"] and await nombre_exists(conn, data.nombre):
        raise NombreAlreadyExistsError
    updated = await update_sucursal(
        conn,
        sucursal_id=branch_id,
        nombre=data.nombre,
        direccion=data.direccion,
        telefono=data.telefono,
        correo=data.correo,
        administrador_id=data.administrador_id,
        administrador_name=data.administrador_name,
        modificado_por=UUID(current_user.sub),
    )
    if not updated:
        raise BranchNotFoundError
    record = await get_sucursal_by_id(conn, branch_id)
    if record is None:
        raise BranchNotFoundError
    return _to_response(record)


async def deactivate_branch(conn: asyncpg.Connection, branch_id: UUID, current_user: TokenData) -> None:
    deactivated = await deactivate_sucursal(conn, branch_id, UUID(current_user.sub))
    if not deactivated:
        raise BranchNotFoundError

async def reactivate_branch(conn: asyncpg.Connection, branch_id: UUID, current_user: TokenData) -> None:
    reactivated = await reactivate_sucursal(conn, branch_id, UUID(current_user.sub))
    if not reactivated:
        raise BranchNotFoundError