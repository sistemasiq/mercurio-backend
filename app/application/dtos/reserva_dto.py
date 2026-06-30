from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class AgregarExtraDTO:
    """Datos de entrada para agregar un extra a una reservación existente."""

    reservacion_id: UUID
    extra_id: UUID
    cantidad: int
    creado_por: UUID | None = None
