from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field, StringConstraints


class TiposEventoBase(BaseModel):
    nombre: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
    descripcion: str | None = None


class TiposEventoCreate(TiposEventoBase):
    pass


class TiposEventoUpdate(BaseModel):
    nombre: str | None = Field(None, max_length=100)
    descripcion: str | None = None
    activo: bool | None = None


class TiposEventoOut(TiposEventoBase):
    id: UUID
    activo: bool
    creado: datetime
    creado_por: UUID | None
    modificado: datetime | None
    modificado_por: UUID | None

    model_config = {"from_attributes": True}
