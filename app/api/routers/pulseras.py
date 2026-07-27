from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, status

from app.api.deps import require_permission
from app.core.database import get_db
from app.schemas.auth import TokenData
from app.schemas.pulseras import PulseraCrear, PulseraOut, PulseraResponse, PulseraUpdate
from app.services import pulseras as pulseras_service
from app.services.pulseras import get_pulseras_disponibles_by_sucursal_id

router = APIRouter(prefix="/api/pulseras", tags=["Pulseras"])


@router.get(
    "/sucursal/{sucursal_id}",
    response_model=list[PulseraResponse],
    summary="Listar pulseras disponibles",
    description="Obtiene pulseras disponibles por sucursal.",
)
async def get_pulseras_disponibles(
    sucursal_id: UUID,
    conn: asyncpg.Connection = Depends(get_db),
    _: TokenData = Depends(require_permission("estancias:checkin")),
) -> list[PulseraResponse]:
    return await get_pulseras_disponibles_by_sucursal_id(conn, sucursal_id)


@router.get(
    "/admin/{sucursal_id}",
    response_model=list[PulseraOut],
    summary="Listar todas las pulseras de una sucursal (admin)",
)
async def listar_pulseras_admin(
    sucursal_id: UUID,
    conn: asyncpg.Connection = Depends(get_db),
    _: TokenData = Depends(require_permission("pulseras:listar")),
) -> list[PulseraOut]:
    return await pulseras_service.listar_todas(conn, sucursal_id)


@router.post("", response_model=PulseraOut, status_code=status.HTTP_201_CREATED)
async def crear_pulsera(
    body: PulseraCrear,
    conn: asyncpg.Connection = Depends(get_db),
    current_user: TokenData = Depends(require_permission("pulseras:crear")),
) -> PulseraOut:
    return await pulseras_service.crear(conn, body, UUID(current_user.sub))


@router.patch("/{pulsera_id}", response_model=PulseraOut)
async def actualizar_pulsera(
    pulsera_id: UUID,
    body: PulseraUpdate,
    conn: asyncpg.Connection = Depends(get_db),
    _: TokenData = Depends(require_permission("pulseras:editar")),
) -> PulseraOut:
    return await pulseras_service.actualizar(conn, pulsera_id, body)


@router.delete("/{pulsera_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_pulsera(
    pulsera_id: UUID,
    conn: asyncpg.Connection = Depends(get_db),
    _: TokenData = Depends(require_permission("pulseras:eliminar")),
) -> None:
    await pulseras_service.eliminar(conn, pulsera_id)
