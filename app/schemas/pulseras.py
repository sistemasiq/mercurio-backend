from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PulseraResponse(BaseModel):
    id: UUID
    pulseraRfid: str  # noqa: N815 — camelCase requerido por el contrato JSON del frontend

    model_config = ConfigDict(from_attributes=True)


class PulseraCrear(BaseModel):
    sucursal_id: UUID
    pulsera_rfid: str = Field(..., max_length=10)


class PulseraUpdate(BaseModel):
    pulsera_rfid: str | None = Field(None, max_length=10)
    activo: bool | None = None


class PulseraOut(BaseModel):
    id: UUID
    sucursal_id: UUID
    pulsera_rfid: str
    activo: bool
    creado: datetime | None
    creado_por: UUID | None
    modificado: datetime | None
    modificado_por: UUID | None

    model_config = {"from_attributes": True}
