from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, status

import app.services.extras as svc
from app.api.deps import require_permission
from app.core.database import get_db
from app.core.roles import ROL_SISTEMA
from app.core.scope import sucursal_scope
from app.schemas.auth import TokenData
from app.schemas.extras import ExtrasCrear, ExtrasOut, ExtrasUpdate

router = APIRouter(prefix="/api/extras", tags=["Extras"])


@router.get("", response_model=list[ExtrasOut])
async def listar_extras(
    conn: asyncpg.Connection = Depends(get_db),
    current_user: TokenData = Depends(require_permission("extras:listar")),
) -> list[ExtrasOut]:
    scope = sucursal_scope(current_user)
    return await svc.listar(conn, UUID(scope) if scope is not None else None)


@router.get("/{extra_id}", response_model=ExtrasOut)
async def obtener_extra(
    extra_id: UUID,
    conn: asyncpg.Connection = Depends(get_db),
    _: TokenData = Depends(require_permission("extras:ver")),
) -> ExtrasOut:
    return await svc.obtener(conn, extra_id)


@router.post("", response_model=ExtrasOut, status_code=status.HTTP_201_CREATED)
async def crear_extra(
    body: ExtrasCrear,
    conn: asyncpg.Connection = Depends(get_db),
    current_user: TokenData = Depends(require_permission("extras:crear")),
) -> ExtrasOut:
    # sucursal_id siempre se deriva del usuario autenticado, nunca se confía
    # en lo que mande el cliente -- ya no existe el concepto de extra
    # "global" (sucursal_id NULL).
    if current_user.role == ROL_SISTEMA:
        if body.sucursal_id is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Debes indicar sucursal_id (AdministradorSistema ve todas).",
            )
    else:
        body.sucursal_id = current_user.branch_id
    return await svc.crear(conn, body)


@router.patch("/{extra_id}", response_model=ExtrasOut)
async def actualizar_extra(
    extra_id: UUID,
    body: ExtrasUpdate,
    conn: asyncpg.Connection = Depends(get_db),
    _: TokenData = Depends(require_permission("extras:editar")),
) -> ExtrasOut:
    return await svc.actualizar(conn, extra_id, body)


@router.delete("/{extra_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_extra(
    extra_id: UUID,
    conn: asyncpg.Connection = Depends(get_db),
    _: TokenData = Depends(require_permission("extras:eliminar")),
) -> None:
    await svc.eliminar(conn, extra_id)
