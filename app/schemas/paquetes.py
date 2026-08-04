from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any
from uuid import UUID

from pydantic import BaseModel, Field, StringConstraints, model_validator


class PaqueteProductoItem(BaseModel):
    producto_id: UUID
    cantidad: int = Field(..., ge=1)


class PaquetesBase(BaseModel):
    sucursal_id: UUID
    nombre: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=150)]
    descripcion: str | None = None
    # Rango de invitados que soporta el paquete. El asistente de reservación solo
    # ofrece los paquetes cuyo rango cubre los niños que pidió el cliente.
    min_invitados: int = Field(1, gt=0)
    max_invitados: int = Field(10, gt=0)
    precio_base: Decimal = Field(..., ge=0)
    # Se cobra por cada invitado del evento: precio_base + precio_pulsera * invitados.
    precio_pulsera: Decimal = Field(Decimal(0), ge=0)

    @model_validator(mode="after")
    def validar_rango(self) -> "PaquetesBase":
        if self.max_invitados < self.min_invitados:
            raise ValueError("max_invitados debe ser mayor o igual que min_invitados")
        return self


class PaquetesCreate(PaquetesBase):
    productos_incluidos: list[PaqueteProductoItem] | None = None


class PaquetesUpdate(BaseModel):
    nombre: str | None = Field(None, max_length=150)
    descripcion: str | None = None
    min_invitados: int | None = Field(None, gt=0)
    max_invitados: int | None = Field(None, gt=0)
    precio_base: Decimal | None = Field(None, ge=0)
    precio_pulsera: Decimal | None = Field(None, ge=0)
    activo: bool | None = None
    productos_incluidos: list[PaqueteProductoItem] | None = None

    @model_validator(mode="after")
    def validar_rango(self) -> "PaquetesUpdate":
        # Solo valida cuando llegan ambos extremos; si viene uno suelto, el CHECK
        # de la BD atrapa el rango invertido contra el valor ya guardado.
        if (
            self.min_invitados is not None
            and self.max_invitados is not None
            and self.max_invitados < self.min_invitados
        ):
            raise ValueError("max_invitados debe ser mayor o igual que min_invitados")
        return self


class PaquetesOut(PaquetesBase):
    id: UUID
    activo: bool
    creado: datetime
    creado_por: UUID | None
    modificado: datetime | None
    modificado_por: UUID | None
    productos_incluidos: list[dict[str, Any]] | None = None
    # Solo los puebla el listado; en crear/actualizar/obtener quedan en 0 / None.
    contrataciones: int = 0
    ultima_contratacion: datetime | None = None

    model_config = {"from_attributes": True}
