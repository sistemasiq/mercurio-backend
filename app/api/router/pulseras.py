from typing import List
from uuid import UUID
from app.core.database import get_db
import asyncpg
from starlette import status

from fastapi import APIRouter, Depends
from app.schemas.pulseras import PulseraResponse

from app.services.pulseras import get_pulseras_by_sucursal_id


router = APIRouter(prefix="/api/pulseras", tags=["Pulseras"])


@router.get(
   "/{sucursal_id}",
   response_model=List[PulseraResponse],
   summary="Listar pulseras disponibles",
   description="Obtiene pulseras activas que no están siendo utilizadas en estancias en curso."
)
async def get_pulseras_disponibles(
   sucursal_id: UUID,
   conn: asyncpg.Connection = Depends(get_db)
):

   return get_pulseras_by_sucursal_id(conn,sucursal_id)
