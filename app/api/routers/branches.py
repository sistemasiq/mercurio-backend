from __future__ import annotations

from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.api.deps import require_role
from app.core.database import get_db
from app.schemas.auth import RoleEnum, TokenData
from app.schemas.branch import BranchCreateRequest, BranchResponse, BranchUpdateRequest
from app.services.branch_service import (
    BranchNotFoundError,
    InsufficientPermissionsError,
    NombreAlreadyExistsError,
    create_branch,
    delete_branch,
    get_branch,
    list_branches,
    update_branch,
)

router = APIRouter(prefix="/api/branches", tags=["branches"])

_sistema_only = require_role(RoleEnum.administrador_sistema)
_admin_roles = require_role(RoleEnum.administrador_sistema, RoleEnum.administrador)

_NOT_FOUND = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail={"code": "BRANCH_NOT_FOUND", "message": "Sucursal no encontrada."},
)
_FORBIDDEN = HTTPException(
    status_code=status.HTTP_403_FORBIDDEN,
    detail={"code": "FORBIDDEN", "message": "No tienes permiso para esta acción."},
)
_CONFLICT = HTTPException(
    status_code=status.HTTP_409_CONFLICT,
    detail={"code": "NOMBRE_ALREADY_EXISTS", "message": "Ya existe una sucursal con ese nombre."},
)


@router.get("", response_model=list[BranchResponse])
async def get_branches(
    current_user: TokenData = Depends(_admin_roles),
    conn: asyncpg.Connection = Depends(get_db),
) -> list[BranchResponse]:
    return await list_branches(conn, current_user)


@router.post("", response_model=BranchResponse, status_code=status.HTTP_201_CREATED)
async def post_branch(
    body: BranchCreateRequest,
    current_user: TokenData = Depends(_sistema_only),
    conn: asyncpg.Connection = Depends(get_db),
) -> BranchResponse:
    try:
        return await create_branch(conn, body, current_user)
    except NombreAlreadyExistsError:
        raise _CONFLICT from None


@router.get("/{branch_id}", response_model=BranchResponse)
async def get_branch_endpoint(
    branch_id: UUID,
    current_user: TokenData = Depends(_admin_roles),
    conn: asyncpg.Connection = Depends(get_db),
) -> BranchResponse:
    try:
        return await get_branch(conn, branch_id, current_user)
    except BranchNotFoundError:
        raise _NOT_FOUND from None
    except InsufficientPermissionsError:
        raise _FORBIDDEN from None


@router.put("/{branch_id}", response_model=BranchResponse)
async def put_branch(
    branch_id: UUID,
    body: BranchUpdateRequest,
    current_user: TokenData = Depends(_sistema_only),
    conn: asyncpg.Connection = Depends(get_db),
) -> BranchResponse:
    try:
        return await update_branch(conn, branch_id, body, current_user)
    except BranchNotFoundError:
        raise _NOT_FOUND from None
    except NombreAlreadyExistsError:
        raise _CONFLICT from None


@router.delete("/{branch_id}")
async def delete_branch_endpoint(
    branch_id: UUID,
    current_user: TokenData = Depends(_sistema_only),
    conn: asyncpg.Connection = Depends(get_db),
) -> Response:
    try:
        await delete_branch(conn, branch_id, current_user)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except BranchNotFoundError:
        raise _NOT_FOUND from None
