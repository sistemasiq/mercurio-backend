from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, status

import app.services.pagos_reservacion as svc
from app.api.deps import apertura_operando_id, require_permission
from app.core.database import get_db
from app.core.scope import sucursal_scope
from app.schemas.auth import TokenData
from app.schemas.pagos_reservacion import (
    PagosReservacionCreate,
    PagosReservacionOut,
    PagosReservacionUpdate,
)

router = APIRouter(prefix="/api/pagos-reservacion", tags=["Pagos de Reservación"])


@router.get("", response_model=list[PagosReservacionOut])
async def listar_pagos(
    conn: asyncpg.Connection = Depends(get_db),
    current_user: TokenData = Depends(require_permission("reservaciones:gestionar_pagos")),
) -> list[PagosReservacionOut]:
    return await svc.listar_todos(conn, sucursal_scope(current_user))


@router.get("/reservacion/{reservacion_id}", response_model=list[PagosReservacionOut])
async def listar_pagos_reservacion(
    reservacion_id: UUID,
    conn: asyncpg.Connection = Depends(get_db),
    current_user: TokenData = Depends(require_permission("reservaciones:gestionar_pagos")),
) -> list[PagosReservacionOut]:
    return await svc.listar_por_reservacion(conn, reservacion_id, current_user)


@router.get("/{pago_id}", response_model=PagosReservacionOut)
async def obtener_pago(
    pago_id: UUID,
    conn: asyncpg.Connection = Depends(get_db),
    _: TokenData = Depends(require_permission("reservaciones:gestionar_pagos")),
) -> PagosReservacionOut:
    return await svc.obtener(conn, pago_id)


@router.post("", response_model=PagosReservacionOut, status_code=status.HTTP_201_CREATED)
async def crear_pago(
    body: PagosReservacionCreate,
    conn: asyncpg.Connection = Depends(get_db),
    current_user: TokenData = Depends(require_permission("reservaciones:gestionar_pagos")),
    apertura_id: str = Depends(apertura_operando_id),
) -> PagosReservacionOut:
    return await svc.crear(conn, body, UUID(current_user.sub), apertura_id)


@router.patch("/{pago_id}", response_model=PagosReservacionOut)
async def actualizar_pago(
    pago_id: UUID,
    body: PagosReservacionUpdate,
    conn: asyncpg.Connection = Depends(get_db),
    _: TokenData = Depends(require_permission("reservaciones:gestionar_pagos")),
) -> PagosReservacionOut:
    return await svc.actualizar(conn, pago_id, body)


@router.delete("/{pago_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_pago(
    pago_id: UUID,
    conn: asyncpg.Connection = Depends(get_db),
    _: TokenData = Depends(require_permission("reservaciones:gestionar_pagos")),
) -> None:
    await svc.eliminar(conn, pago_id)
