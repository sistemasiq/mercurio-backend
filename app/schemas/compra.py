from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class DetalleCompraItem(BaseModel):
    insumo_id: UUID
    unidad_medida_id: UUID | None = None
    presentacion_id: UUID | None = None
    cantidad: Decimal = Field(..., gt=0)
    costo_unitario: Decimal = Field(..., ge=0)

    @model_validator(mode="after")
    def validar_una_unidad(self) -> "DetalleCompraItem":
        if (self.unidad_medida_id is None) == (self.presentacion_id is None):
            raise ValueError("Indica unidad_medida_id o presentacion_id, no ambos ni ninguno.")
        return self


class CompraCrear(BaseModel):
    sucursal_id: UUID
    proveedor_id: UUID
    notas: str | None = None
    # Monto de IVA de la orden (se captura; el total sigue siendo la suma de líneas).
    iva: Decimal = Field(Decimal("0"), ge=0)
    detalles: list[DetalleCompraItem] = Field(..., min_length=1)


class CompraUpdate(BaseModel):
    notas: str | None = None
    activo: bool | None = None


class CompraEditar(BaseModel):
    """Edición completa de una compra en estado 'P' (reemplaza proveedor,
    notas y todas las líneas)."""

    proveedor_id: UUID
    notas: str | None = None
    # None conserva el IVA ya capturado.
    iva: Decimal | None = Field(None, ge=0)
    detalles: list[DetalleCompraItem] = Field(..., min_length=1)


class LineaRecepcion(BaseModel):
    detalle_id: UUID
    cantidad: Decimal = Field(..., gt=0)


class RecibirCompraRequest(BaseModel):
    """Recepción parcial: qué líneas y cuánto de cada una llegó en esta vuelta.
    Sin `lineas`, se recibe todo lo pendiente."""

    lineas: list[LineaRecepcion] | None = None


class DetalleCompraOut(BaseModel):
    id: UUID
    insumo_id: UUID
    insumo_nombre: str
    unidad_medida_id: UUID | None
    unidad_medida_codigo: str | None
    presentacion_id: UUID | None
    presentacion_nombre: str | None
    cantidad: Decimal
    cantidad_recibida: Decimal
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
    iva: Decimal = Decimal("0")
    # Folio de OC secuencial por sucursal; None en compras anteriores a la 066.
    folio: str | None = None
    notas: str | None
    activo: bool
    creado: datetime
    creado_por: UUID | None
    modificado: datetime | None
    modificado_por: UUID | None
    detalles: list[DetalleCompraOut] = []

    model_config = {"from_attributes": True}
