from pydantic import BaseModel
from uuid import UUID

class PulseraResponse(BaseModel):
   id: UUID
   pulsera_rfid: str
