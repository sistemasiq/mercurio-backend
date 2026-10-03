"""Shapes para GET /reservaciones/disponibilidad: bloques de horario de la
sucursal marcados como ocupados o libres para una fecha dada."""

from datetime import time
from uuid import UUID

from pydantic import BaseModel


class BloqueDisponibilidad(BaseModel):
    hora_inicio: time
    hora_fin: time
    ocupado: bool
    # Reservación que ocupa el bloque, si aplica -- útil para que el front
    # muestre a quién pertenece sin otra consulta.
    reservacion_id: UUID | None = None


class DisponibilidadResponse(BaseModel):
    sucursal_id: UUID
    fecha: str
    bloques: list[BloqueDisponibilidad]
