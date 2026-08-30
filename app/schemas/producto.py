import json
from datetime import datetime
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

TipoProducto = Literal["A", "B", "E", "S", "C"]  # Alimento | Bebida | Estancia | Servicio | Combo


class TramoEstanciaSchema(BaseModel):
    min_horas: int = Field(..., ge=0)
    max_horas: int = Field(..., ge=0)
    precio: Decimal = Field(..., ge=0)


class PrecioEstanciaOut(BaseModel):
    id: UUID
    config_estancia: list[TramoEstanciaSchema]

    model_config = ConfigDict(from_attributes=True)

    @field_validator("config_estancia", mode="before")
    @classmethod
    def parsear_config_estancia(cls, v: Any):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return []
        return v


class ComboItem(BaseModel):
    producto_id: UUID
    cantidad: int = Field(..., ge=1)


class ProductoBase(BaseModel):
    nombre: str = Field(..., max_length=150)
    precio_unitario: Decimal = Field(..., ge=0)
    tipo: TipoProducto
    descripcion: str | None = None
    imagen: str | None = None


class ProductoCrear(ProductoBase):
    sucursal_id: UUID
    productos_combo: list[ComboItem] | None = None
    config_estancia: list[TramoEstanciaSchema] | None = None


class ProductoUpdate(BaseModel):
    nombre: str | None = None
    precio_unitario: Decimal | None = None
    tipo: TipoProducto | None = None
    descripcion: str | None = None
    imagen: str | None = None
    activo: bool | None = None
    productos_combo: list[ComboItem] | None = None
    config_estancia: list[TramoEstanciaSchema] | None = None


class ProductoOut(ProductoBase):
    id: UUID
    sucursal_id: UUID
    activo: bool
    es_combo: bool
    creado: datetime | None = None
    creado_por: UUID | None = None
    modificado: datetime | None = None
    modificado_por: UUID | None = None
    productos_combo: list[dict[str, Any]] | None = None
    config_estancia: list[TramoEstanciaSchema] | None = None

    model_config = {"from_attributes": True}

    @field_validator("config_estancia", mode="before")
    @classmethod
    def parsear_config_estancia(cls, v: Any):
        """Si la BD retorna una cadena de texto JSON en lugar de una lista, la parsea automáticamente."""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return None
        return v