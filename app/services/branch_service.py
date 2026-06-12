from __future__ import annotations

from uuid import UUID

import asyncpg

from app.repositories.branch_repository import (
    SucursalRecord,
    create_sucursal,
    get_all_sucursales,
    get_sucursal_by_id,
    nombre_exists,
)
from app.schemas.auth import RoleEnum, TokenData
from app.schemas.branch import BranchCreateRequest, BranchResponse


class NombreAlreadyExistsError(Exception):
    pass


def _to_response(record: SucursalRecord) -> BranchResponse:
    return BranchResponse(
        id=record["id"],
        nombre=record["nombre"],
        direccion=record["direccion"],
        telefono=record["telefono"],
        is_active=record["activo"],
    )


async def list_branches(conn: asyncpg.Connection, current_user: TokenData) -> list[BranchResponse]:
    if current_user.role == RoleEnum.administrador_sistema:
        records = await get_all_sucursales(conn)
        return [_to_response(r) for r in records]

    if current_user.branch_id is None:
        return []
    record = await get_sucursal_by_id(conn, current_user.branch_id)
    return [_to_response(record)] if record else []


async def create_branch(
    conn: asyncpg.Connection,
    data: BranchCreateRequest,
    current_user: TokenData,
) -> BranchResponse:
    if await nombre_exists(conn, data.nombre):
        raise NombreAlreadyExistsError

    creator_id = UUID(current_user.sub)
    sucursal_id = await create_sucursal(
        conn,
        nombre=data.nombre,
        direccion=data.direccion,
        telefono=data.telefono,
        creado_por=creator_id,
    )

    record = await get_sucursal_by_id(conn, sucursal_id)
    if record is None:
        raise RuntimeError("Error al recuperar la sucursal recién creada")
    return _to_response(record)
