from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, status

import app.services.metodos_pago as svc
from app.api.deps import require_permission
from app.core.database import get_db
from app.core.roles import ROL_SISTEMA
from app.core.scope import sucursal_scope
from app.schemas.auth import TokenData
from app.schemas.metodos_pago import MetodosPagoCreate, MetodosPagoOut, MetodosPagoUpdate

router = APIRouter(prefix="/api/metodos-pago", tags=["Métodos de Pago"])


@router.get("", response_model=list[MetodosPagoOut])
async def listar_metodos_pago(
    conn: asyncpg.Connection = Depends(get_db),
    current_user: TokenData = Depends(require_permission("metodos_pago:listar")),
) -> list[MetodosPagoOut]:
    scope = sucursal_scope(current_user)
    return await svc.listar(conn, UUID(scope) if scope is not None else None)


@router.get("/{metodo_pago_id}", response_model=MetodosPagoOut)
async def obtener_metodo_pago(
    metodo_pago_id: UUID,
    conn: asyncpg.Connection = Depends(get_db),
    _: TokenData = Depends(require_permission("metodos_pago:ver")),
) -> MetodosPagoOut:
    return await svc.obtener(conn, metodo_pago_id)


@router.post("", response_model=MetodosPagoOut, status_code=status.HTTP_201_CREATED)
async def crear_metodo_pago(
    body: MetodosPagoCreate,
    conn: asyncpg.Connection = Depends(get_db),
    current_user: TokenData = Depends(require_permission("metodos_pago:crear")),
) -> MetodosPagoOut:
    # sucursal_id siempre se deriva del usuario autenticado, nunca se confía
    # en lo que mande el cliente -- ya no existe el concepto de método de
    # pago "global" (sucursal_id NULL).
    if current_user.role == ROL_SISTEMA:
        if body.sucursal_id is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Debes indicar sucursal_id (AdministradorSistema ve todas).",
            )
    else:
        body.sucursal_id = current_user.branch_id
    return await svc.crear(conn, body)


@router.patch("/{metodo_pago_id}", response_model=MetodosPagoOut)
async def actualizar_metodo_pago(
    metodo_pago_id: UUID,
    body: MetodosPagoUpdate,
    conn: asyncpg.Connection = Depends(get_db),
    _: TokenData = Depends(require_permission("metodos_pago:editar")),
) -> MetodosPagoOut:
    return await svc.actualizar(conn, metodo_pago_id, body)


@router.delete("/{metodo_pago_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_metodo_pago(
    metodo_pago_id: UUID,
    conn: asyncpg.Connection = Depends(get_db),
    _: TokenData = Depends(require_permission("metodos_pago:eliminar")),
) -> None:
    await svc.eliminar(conn, metodo_pago_id)
