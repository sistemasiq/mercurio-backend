from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class ExtrasBase(BaseModel):
    nombre: str = Field(..., max_length=150)
    descripcion: str | None = None
    precio: Decimal = Field(..., ge=0)
    unidad: Literal["evento", "persona", "hora"] = "evento"


class ExtrasCrear(ExtrasBase):
    # Solo relevante para AdministradorSistema (sin sucursal propia); para
    # cualquier otro rol el router ignora este valor y usa siempre la
    # sucursal del usuario autenticado. Ya no existe el concepto de extra
    # "global" (sucursal_id NULL).
    sucursal_id: UUID | None = None


class ExtrasUpdate(BaseModel):
    nombre: str | None = None
    descripcion: str | None = None
    precio: Decimal | None = None
    unidad: Literal["evento", "persona", "hora"] | None = None
    activo: bool | None = None


class ExtrasOut(ExtrasBase):
    id: UUID
    sucursal_id: UUID | None
    activo: bool
    creado: datetime
    creado_por: UUID | None
    modificado: datetime | None
    modificado_por: UUID | None

    model_config = {"from_attributes": True}
