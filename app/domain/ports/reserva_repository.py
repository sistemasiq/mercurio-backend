from datetime import datetime
from typing import Protocol
from uuid import UUID
from domain.entities.extras import Extras

class ReservaRepository(Protocol):
    """
    Interfaz que define los métodos para interactuar con el repositorio de reservas.
    """

    async def agregar_extra_a_reserva(self, reservacion_id: UUID, extra: Extras, creado_por: str) -> None:
        """
        Agrega un extra a una reservación existente.

        Args:
            reservacion_id (UUID): El ID de la reservación a la que se agregará el extra.
            extra (Extras): El objeto Extra que se agregará a la reservación.
            creado_por (str): El nombre del usuario que está realizando la acción.

        Raises:
            ValueError: Si el ID de la reservación no es válido o si el extra no es válido.
        """
        pass

    async def eliminar_extra_de_reserva(self, reservacion_id: UUID, extra_id: UUID) -> None:
        """
        Elimina un extra de una reservación existente.

        Args:
            reservacion_id (UUID): El ID de la reservación de la que se eliminará el extra.
            extra_id (UUID): El ID del extra que se eliminará de la reservación.

        Raises:
            ValueError: Si el ID de la reservación no es válido o si el ID del extra no es válido.
        """
        pass

    async def guardar_cambios(self) -> None:
        """
        Guarda los cambios realizados en el repositorio de reservas.

        Raises:
            Exception: Si ocurre un error al guardar los cambios.
        """
        pass

    async def obtener_reservacion_por_id(self, reservacion_id: UUID):
        """Obtiene una reservación por su ID.
        Args:
            reservacion_id (UUID): El ID de la reservación a obtener.
        Returns:
            Reservacion: La reservación correspondiente al ID proporcionado.    
        Raises:
            ValueError: Si el ID de la reservación no es válido o si no se encuentra la reservación.
        """
        pass
