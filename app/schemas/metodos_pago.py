from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, Field, StringConstraints

# E = Efectivo | T = Tarjeta (crédito/débito/wallets) | C = Cupón | L = Lealtad
# O = Otro (cualquier método que no encaje en los anteriores, ej. transferencias)
TipoMetodoPago = Literal["E", "T", "C", "L", "O"]


class MetodosPagoBase(BaseModel):
    nombre: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
    descripcion: str | None = None
    # Categoría real usada por el FrontEnd para decidir qué botón/comportamiento
    # de cobro corresponde a este método, independiente del nombre libre que
    # cada sucursal le ponga (ver 036_metodos_pago_tipo.sql).
    tipo: TipoMetodoPago = "O"


class MetodosPagoCreate(MetodosPagoBase):
    # Solo relevante para AdministradorSistema (sin sucursal propia); para
    # cualquier otro rol el router ignora este valor y usa siempre la
    # sucursal del usuario autenticado. Ya no existe el concepto de método
    # de pago "global" (sucursal_id NULL).
    sucursal_id: UUID | None = None


class MetodosPagoUpdate(BaseModel):
    nombre: str | None = Field(None, max_length=100)
    descripcion: str | None = None
    tipo: TipoMetodoPago | None = None
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
