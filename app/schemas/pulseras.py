from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PulseraResponse(BaseModel):
    id: UUID
    pulseraRfid: str  # noqa: N815 — camelCase requerido por el contrato JSON del frontend

    model_config = ConfigDict(from_attributes=True)


class InventarioPulserasOut(BaseModel):
    """Conteo de pulseras de una sucursal, sin exponer el listado.

    Lo consume el asistente de reservación para avisar si el número de niños
    rebasa lo que la sucursal puede pulsear. Se devuelve sólo el número porque
    quien levanta la reservación suele ser Cajero, y ese rol no tiene permiso
    para ver el inventario de pulseras.
    """

    sucursal_id: UUID
    total_activas: int


class PulseraCrear(BaseModel):
    sucursal_id: UUID
    pulsera_rfid: str = Field(..., max_length=50)
    activo: bool = True
    numero_lote: str | None = Field(None, max_length=50)


class PulseraUpdate(BaseModel):
    pulsera_rfid: str | None = Field(None, max_length=50)
    activo: bool | None = None


class PulseraOut(BaseModel):
    id: UUID
    sucursal_id: UUID
    pulsera_rfid: str
    activo: bool
    numero_lote: str | None = None
    creado: datetime | None
    creado_por: UUID | None
    modificado: datetime | None
    modificado_por: UUID | None

    model_config = {"from_attributes": True}
