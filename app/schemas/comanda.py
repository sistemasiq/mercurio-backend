from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional
import uuid

from pydantic import UUID4, BaseModel, Field


class EstadoComanda(str, Enum):
    PENDIENTE = "P"
    EN_PROCESO = "E"
    LISTO = "L"
    ENTREGADO = "T"
    CANCELADO = "C"


# Esquema para los productos dentro de la comanda
class DetalleCreate(BaseModel):
    id: str = Field(..., alias="producto_id")
    nombre: str
    cantidad: int
    precio_unitario: Decimal
    subtotal: Decimal
    notas_especiales: str | None = None
    nombre_combo_padre: str | None = None
    es_hijo_de: str | None = None
    es_hijo_combo: bool = False

    class Config:
        populate_by_name = True


# Esquema para recibir la creación de la comanda
class ComandaCreate(BaseModel):
    notas_generales: str | None = None
    estado_actual: EstadoComanda = EstadoComanda.PENDIENTE
    detalles_comanda: list[DetalleCreate]
    ticket_numero: str
    total_final: Decimal
    sucursal_id: Optional[uuid.UUID] = None


# Esquema de respuesta
class Comanda(BaseModel):
    id: UUID4
    ticket_numero: str
    total_final: Decimal
    sucursal_id: UUID4
    estado_actual: EstadoComanda
    fecha_hora: datetime

    class Config:
        from_attributes = True
