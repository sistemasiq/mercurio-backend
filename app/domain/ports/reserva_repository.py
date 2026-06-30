from decimal import Decimal
from typing import Any, Protocol
from uuid import UUID


class ReservaRepository(Protocol):
    """Puerto del repositorio de reservas usado por los casos de uso del módulo eventos.

    Las implementaciones concretas viven en ``app/infrastructure`` y son las
    únicas que conocen la base de datos.
    """

    async def obtener_reservacion(self, reservacion_id: UUID) -> dict[str, Any] | None: ...

    async def obtener_extra(self, extra_id: UUID) -> dict[str, Any] | None: ...

    async def agregar_extra_a_reserva(
        self,
        *,
        reservacion_id: UUID,
        extra_id: UUID,
        cantidad: int,
        precio_unitario: Decimal,
        creado_por: UUID | None,
    ) -> dict[str, Any]: ...
