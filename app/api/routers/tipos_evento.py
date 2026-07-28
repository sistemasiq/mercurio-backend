from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, status

import app.services.tipos_evento as svc
from app.api.deps import require_permission
from app.core.database import get_db
from app.core.roles import ROL_SISTEMA
from app.core.scope import sucursal_scope
from app.schemas.auth import TokenData
from app.schemas.tipos_evento import TiposEventoCreate, TiposEventoOut, TiposEventoUpdate

router = APIRouter(prefix="/api/tipos-evento", tags=["Tipos de Evento"])


@router.get("", response_model=list[TiposEventoOut])
async def listar_tipos_evento(
    conn: asyncpg.Connection = Depends(get_db),
    current_user: TokenData = Depends(require_permission("tipos_evento:listar")),
) -> list[TiposEventoOut]:
    scope = sucursal_scope(current_user)
    return await svc.listar(conn, UUID(scope) if scope is not None else None)


@router.get("/{tipo_evento_id}", response_model=TiposEventoOut)
async def obtener_tipo_evento(
    tipo_evento_id: UUID,
    conn: asyncpg.Connection = Depends(get_db),
    _: TokenData = Depends(require_permission("tipos_evento:ver")),
) -> TiposEventoOut:
    return await svc.obtener(conn, tipo_evento_id)


@router.post("", response_model=TiposEventoOut, status_code=status.HTTP_201_CREATED)
async def crear_tipo_evento(
    body: TiposEventoCreate,
    conn: asyncpg.Connection = Depends(get_db),
    current_user: TokenData = Depends(require_permission("tipos_evento:crear")),
) -> TiposEventoOut:
    # sucursal_id siempre se deriva del usuario autenticado, nunca se confía
    # en lo que mande el cliente -- ya no existe el concepto de tipo de
    # evento "global" (sucursal_id NULL).
    if current_user.role == ROL_SISTEMA:
        if body.sucursal_id is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Debes indicar sucursal_id (AdministradorSistema ve todas).",
            )
    else:
        body.sucursal_id = current_user.branch_id
    return await svc.crear(conn, body)


@router.patch("/{tipo_evento_id}", response_model=TiposEventoOut)
async def actualizar_tipo_evento(
    tipo_evento_id: UUID,
    body: TiposEventoUpdate,
    conn: asyncpg.Connection = Depends(get_db),
    _: TokenData = Depends(require_permission("tipos_evento:editar")),
) -> TiposEventoOut:
    return await svc.actualizar(conn, tipo_evento_id, body)


@router.delete("/{tipo_evento_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_tipo_evento(
    tipo_evento_id: UUID,
    conn: asyncpg.Connection = Depends(get_db),
    _: TokenData = Depends(require_permission("tipos_evento:eliminar")),
) -> None:
    await svc.eliminar(conn, tipo_evento_id)
