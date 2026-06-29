from pydantic import BaseModel
from uuid import UUID

class PagoIn(BaseModel):
   metodoPagoId: UUID
   monto: float
