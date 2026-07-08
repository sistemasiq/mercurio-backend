from typing import Any
from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends

from app.api.deps import require_permission
from app.core.database import get_db
from app.schemas.auth import TokenData
from app.schemas.pulseras import PulseraResponse
from app.services.pulseras import get_pulseras_disponibles_by_sucursal_id

router = APIRouter(prefix="/api/pulseras", tags=["Pulseras"])


@router.get(
    "/{sucursal_id}",
    response_model=list[PulseraResponse],
    summary="Listar pulseras disponibles",
    description="Obtiene pulseras disponibles por sucursal.",
)
async def get_pulseras_disponibles(
    sucursal_id: UUID,
    conn: asyncpg.Connection = Depends(get_db),
    _: TokenData = Depends(require_permission("estancias:checkin")),
) -> list[dict[str, Any]]:
    return await get_pulseras_disponibles_by_sucursal_id(conn, sucursal_id)
