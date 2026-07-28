from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field, StringConstraints


class MetodosPagoBase(BaseModel):
    nombre: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
    descripcion: str | None = None


class MetodosPagoCreate(MetodosPagoBase):
    # Solo relevante para AdministradorSistema (sin sucursal propia); para
    # cualquier otro rol el router ignora este valor y usa siempre la
    # sucursal del usuario autenticado. Ya no existe el concepto de método
    # de pago "global" (sucursal_id NULL).
    sucursal_id: UUID | None = None


class MetodosPagoUpdate(BaseModel):
    nombre: str | None = Field(None, max_length=100)
    descripcion: str | None = None
    activo: bool | None = None


class MetodosPagoOut(MetodosPagoBase):
    id: UUID
    sucursal_id: UUID | None
    activo: bool
    creado: datetime
    creado_por: UUID | None
    modificado: datetime | None
    modificado_por: UUID | None

    model_config = {"from_attributes": True}
