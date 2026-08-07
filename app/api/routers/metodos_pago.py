from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, status

import app.services.metodos_pago as svc
from app.api.deps import require_permission
from app.core.database import get_db
from app.core.roles import ROL_SISTEMA
from app.core.scope import sucursal_scope
from app.schemas.auth import TokenData
from app.schemas.metodos_pago import MetodosPagoActivacion, MetodosPagoOut, MetodosPagoUpdate

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
    current_user: TokenData = Depends(require_permission("metodos_pago:ver")),
) -> MetodosPagoOut:
    scope = sucursal_scope(current_user)
    return await svc.obtener(conn, metodo_pago_id, UUID(scope) if scope is not None else None)


@router.patch("/{metodo_pago_id}", response_model=MetodosPagoOut)
async def actualizar_catalogo_metodo_pago(
    metodo_pago_id: UUID,
    body: MetodosPagoUpdate,
    conn: asyncpg.Connection = Depends(get_db),
    current_user: TokenData = Depends(require_permission("metodos_pago:editar")),
) -> MetodosPagoOut:
    # Nombre/descripción son el catálogo global -- solo AdministradorSistema
    # puede tocarlos, para que ninguna sucursal rompa la consistencia que
    # motivó que este catálogo sea fijo.
    if current_user.role != ROL_SISTEMA:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo AdministradorSistema puede editar el catálogo de métodos de pago.",
        )
    scope = sucursal_scope(current_user)
    return await svc.actualizar_catalogo(
        conn, metodo_pago_id, body, UUID(scope) if scope is not None else None
    )


@router.patch("/{metodo_pago_id}/activacion", response_model=MetodosPagoOut)
async def activar_metodo_pago(
    metodo_pago_id: UUID,
    body: MetodosPagoActivacion,
    conn: asyncpg.Connection = Depends(get_db),
    current_user: TokenData = Depends(require_permission("metodos_pago:editar")),
) -> MetodosPagoOut:
    # Activar/desactivar es una decisión de cada sucursal; se deriva siempre
    # de la sucursal del usuario autenticado, nunca del cliente. Administrador
    # Sistema no tiene sucursal propia, así que no puede usar este endpoint.
    if current_user.branch_id is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Este usuario no tiene una sucursal asignada para activar/desactivar "
            "métodos de pago.",
        )
    return await svc.set_activacion(
        conn, metodo_pago_id, current_user.branch_id, body.activo, UUID(current_user.sub)
    )
