from pydantic import BaseModel,Field
from typing import Optional

class NinoIn(BaseModel):
   nombreCompleto: str
   edad: int = Field(ge=1, le=99)
   notas: Optional[str] = None
