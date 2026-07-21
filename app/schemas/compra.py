from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class DetalleCompraItem(BaseModel):
    insumo_id: UUID
    unidad_medida_id: UUID
    cantidad: Decimal = Field(..., gt=0)
    costo_unitario: Decimal = Field(..., ge=0)


class CompraCrear(BaseModel):
    sucursal_id: UUID
    proveedor_id: UUID
    notas: str | None = None
    detalles: list[DetalleCompraItem] = Field(..., min_length=1)


class CompraUpdate(BaseModel):
    notas: str | None = None
    activo: bool | None = None


class DetalleCompraOut(BaseModel):
    id: UUID
    insumo_id: UUID
    insumo_nombre: str
    unidad_medida_id: UUID
    unidad_medida_codigo: str
    cantidad: Decimal
    costo_unitario: Decimal
    subtotal: Decimal

    model_config = {"from_attributes": True}


class CompraOut(BaseModel):
    id: UUID
    sucursal_id: UUID
    proveedor_id: UUID
    proveedor_nombre: str
    estado: str
    fecha_pedido: datetime
    fecha_recepcion: datetime | None
    total: Decimal
    notas: str | None
    activo: bool
    creado: datetime
    creado_por: UUID | None
    modificado: datetime | None
    modificado_por: UUID | None
    detalles: list[DetalleCompraOut] = []

    model_config = {"from_attributes": True}
