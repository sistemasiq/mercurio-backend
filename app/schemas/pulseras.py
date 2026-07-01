from uuid import UUID

from pydantic import BaseModel


class PulseraResponse(BaseModel):
    id: UUID
    pulsera_rfid: str
