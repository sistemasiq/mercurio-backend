from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from app.api.deps import get_current_user
from app.application.dtos.reserva_dto import AgregarExtraDTO
from app.application.use_cases.agregar_extra_a_reserva import AgregarExtraAReservaUseCase
from app.core.database import get_db
from app.domain.exceptions.eventos import (
    ExtraInvalido,
    ExtraNoEncontrado,
    ReservaNoEncontrada,
)
from app.exceptions import Conflicto, NoEncontrado
from app.infrastructure.repositories.reserva_repository_asyncpg import (
    ReservaRepositoryAsyncpg,
)
from app.schemas.auth import TokenData
from app.schemas.reservacion_extras import ReservacionExtrasOut

router = APIRouter(prefix="/api/eventos", tags=["Eventos (DDD)"])


class AgregarExtraRequest(BaseModel):
    extra_id: UUID
    cantidad: int = Field(..., ge=1)


@router.post(
    "/reservaciones/{reservacion_id}/extras",
    response_model=ReservacionExtrasOut,
    status_code=status.HTTP_201_CREATED,
)
async def agregar_extra_a_reserva(
    reservacion_id: UUID,
    body: AgregarExtraRequest,
    conn: asyncpg.Connection = Depends(get_db),
    user: TokenData = Depends(get_current_user),
):
    """Caso de uso DDD: agrega un extra a una reservación del módulo eventos."""
    caso_uso = AgregarExtraAReservaUseCase(ReservaRepositoryAsyncpg(conn))
    dto = AgregarExtraDTO(
        reservacion_id=reservacion_id,
        extra_id=body.extra_id,
        cantidad=body.cantidad,
        creado_por=user.sub,
    )
    try:
        registro = await caso_uso.execute(dto)
    except ReservaNoEncontrada:
        raise NoEncontrado("Reservación") from None
    except ExtraNoEncontrado:
        raise NoEncontrado("Extra") from None
    except ExtraInvalido as exc:
        raise Conflicto(str(exc)) from None
    return ReservacionExtrasOut.model_validate(registro)
