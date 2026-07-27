from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


class UnidadMedidaOut(BaseModel):
    id: UUID
    codigo: str
    nombre: str
    tipo: str
    factor_a_base: Decimal
    activo: bool

    model_config = {"from_attributes": True}
