from datetime import datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field, StringConstraints


class InsumoBase(BaseModel):
    nombre: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=150)]
    descripcion: str | None = None
    unidad_base_id: UUID
    unidad_compra_id: UUID
    stock_minimo: Decimal = Field(Decimal("0"), ge=0)
    punto_reorden: Decimal | None = Field(None, ge=0)
    stock_maximo: Decimal | None = Field(None, ge=0)
    costo_unitario: Decimal | None = Field(None, ge=0)
    proveedor_principal_id: UUID | None = None


class InsumoCrear(InsumoBase):
    sucursal_id: UUID
    stock_inicial: Decimal = Field(Decimal("0"), ge=0)


class InsumoUpdate(BaseModel):
    """No permite cambiar unidad_base_id/unidad_compra_id ni stock_actual una
    vez creado el insumo: la unidad define en qué se guarda el stock (cambiarla
    requeriría reconvertir el stock existente) y stock_actual solo se moverá
    a través de movimientos_inventario en fase 3."""

    nombre: str | None = Field(None, max_length=150)
    descripcion: str | None = None
    stock_minimo: Decimal | None = Field(None, ge=0)
    punto_reorden: Decimal | None = Field(None, ge=0)
    stock_maximo: Decimal | None = Field(None, ge=0)
    costo_unitario: Decimal | None = Field(None, ge=0)
    proveedor_principal_id: UUID | None = None
    activo: bool | None = None


class InsumoOut(InsumoBase):
    id: UUID
    sucursal_id: UUID
    stock_actual: Decimal
    activo: bool
    creado: datetime | None
    creado_por: UUID | None
    modificado: datetime | None
    modificado_por: UUID | None

    model_config = {"from_attributes": True}


class InsumoAlertasOut(BaseModel):
    """Insumos de la sucursal que necesitan atención de compra. `criticos` están
    por debajo del stock mínimo; `por_reordenar` están por debajo del punto de
    reorden pero todavía sobre el mínimo."""

    criticos: list[InsumoOut]
    por_reordenar: list[InsumoOut]


class InsumoRecetaInversaOut(BaseModel):
    """Una fila de receta vista desde el insumo: qué producto A/B lo consume y en
    qué cantidad (expresada en la unidad base del insumo, por 1 unidad de
    producto). El cálculo de "rinde para N unidades" lo hace el FrontEnd a partir
    de stock_actual / cantidad."""

    insumo_id: UUID
    producto_id: UUID
    producto_nombre: str
    cantidad: Decimal

    model_config = {"from_attributes": True}
