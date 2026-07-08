from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

TipoProducto = Literal["A", "B", "E", "S"]  # Alimento | Bebida | Estancia | Servicio


class ProductoBase(BaseModel):
    nombre: str = Field(..., max_length=150)
    precio_unitario: Decimal = Field(..., ge=0)
    tipo: TipoProducto
    descripcion: str | None = None
    imagen: str | None = None


class ProductoCrear(ProductoBase):
    sucursal_id: UUID


class ProductoUpdate(BaseModel):
    nombre: str | None = None
    precio_unitario: Decimal | None = None
    tipo: TipoProducto | None = None
    descripcion: str | None = None
    imagen: str | None = None
    activo: bool | None = None


class ProductoOut(ProductoBase):
    id: UUID
    sucursal_id: UUID
    activo: bool
    creado: datetime | None
    creado_por: UUID | None
    modificado: datetime | None
    modificado_por: UUID | None

    model_config = {"from_attributes": True}
