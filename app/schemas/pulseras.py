from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class PulseraResponse(BaseModel):
    id: UUID
    pulsera_rfid: str


class PulseraCrear(BaseModel):
    sucursal_id: UUID
    pulsera_rfid: str = Field(..., max_length=50)


class PulseraUpdate(BaseModel):
    pulsera_rfid: str | None = Field(None, max_length=50)
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
