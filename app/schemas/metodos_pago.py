from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, StringConstraints

# E = Efectivo | T = Tarjeta (crédito/débito/wallets) | C = Cupón | L = Lealtad
# O = Otro (cualquier método que no encaje en los anteriores, ej. transferencias)
TipoMetodoPago = Literal["E", "T", "C", "L", "O"]


class MetodosPagoUpdate(BaseModel):
    """Edición del catálogo global -- solo AdministradorSistema. El `tipo` no
    se edita: es la identidad fija de cada una de las 5 filas."""

    nombre: (
        Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
        | None
    ) = None
    descripcion: str | None = None


class MetodosPagoActivacion(BaseModel):
    activo: bool


class MetodosPagoOut(BaseModel):
    id: UUID
    nombre: str
    descripcion: str | None
    tipo: TipoMetodoPago
    # Resuelto contra sucursal_metodos_pago para la sucursal del usuario
    # autenticado -- no es una columna de metodos_pago.
    activo: bool
    creado: datetime
    creado_por: UUID | None
    modificado: datetime | None
    modificado_por: UUID | None

    model_config = {"from_attributes": True}
