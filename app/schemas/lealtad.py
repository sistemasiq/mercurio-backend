from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ConfiguracionLealtadBase(BaseModel):
    porcentaje_retorno: float = Field(0, ge=0, le=100)
    dias_caducidad: int = Field(..., gt=0)
    valor_punto: float = Field(1.00, gt=0)
    activo: bool = True


class ConfiguracionLealtadOut(ConfiguracionLealtadBase):
    sucursal_id: UUID
    creado: datetime
    creado_por: UUID | None
    modificado: datetime | None
    modificado_por: UUID | None

    model_config = {"from_attributes": True}
