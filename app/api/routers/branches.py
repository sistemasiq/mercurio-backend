from __future__ import annotations

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import require_role
from app.core.database import get_db
from app.schemas.auth import RoleEnum, TokenData
from app.schemas.branch import BranchCreateRequest, BranchResponse
from app.services.branch_service import NombreAlreadyExistsError, create_branch, list_branches

router = APIRouter(prefix="/api/branches", tags=["branches"])

_sistema_only = require_role(RoleEnum.administrador_sistema)
_admin_roles = require_role(RoleEnum.administrador_sistema, RoleEnum.administrador)


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
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "NOMBRE_ALREADY_EXISTS",
                "message": "Ya existe una sucursal con ese nombre.",
            },
        ) from None
