from uuid import UUID
from pydantic import BaseModel, ConfigDict


class PulseraResponse(BaseModel):
    id: UUID
    pulseraRfid: str

    model_config = ConfigDict(from_attributes=True)
