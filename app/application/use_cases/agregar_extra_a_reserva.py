from typing import Any

from app.application.dtos.reserva_dto import AgregarExtraDTO
from app.domain.exceptions.eventos import (
    ExtraInvalido,
    ExtraNoEncontrado,
    ReservaNoEncontrada,
)
from app.domain.ports.reserva_repository import ReservaRepository


class AgregarExtraAReservaUseCase:
    """Caso de uso: agregar un extra a una reservación.

    Valida que la reservación y el extra existan, toma el precio vigente del
    extra y delega la persistencia en el repositorio (puerto).
    """

    def __init__(self, reserva_repository: ReservaRepository) -> None:
        self.reserva_repository = reserva_repository

    async def execute(self, dto: AgregarExtraDTO) -> dict[str, Any]:
        if dto.cantidad < 1:
            raise ExtraInvalido("La cantidad debe ser al menos 1.")

        reserva = await self.reserva_repository.obtener_reservacion(dto.reservacion_id)
        if not reserva or not reserva["activo"]:
            raise ReservaNoEncontrada("La reservación no existe.")

        extra = await self.reserva_repository.obtener_extra(dto.extra_id)
        if not extra or not extra["activo"]:
            raise ExtraNoEncontrado("El extra no existe.")

        return await self.reserva_repository.agregar_extra_a_reserva(
            reservacion_id=dto.reservacion_id,
            extra_id=dto.extra_id,
            cantidad=dto.cantidad,
            precio_unitario=extra["precio"],
            creado_por=dto.creado_por,
        )
