from pydantic import BaseModel, UUID4, Field
from typing import List, Optional
from decimal import Decimal
from datetime import datetime
from enum import Enum

class EstadoComanda(str, Enum):
    PENDIENTE = 'P'
    EN_PROCESO = 'E'
    LISTO = 'L'
    ENTREGADO = 'T'
    CANCELADO = 'C'

# Esquema para los productos dentro de la comanda
class DetalleCreate(BaseModel):
    id: str = Field(..., alias="producto_id")
    nombre: str
    cantidad: int
    precio_unitario: Decimal
    subtotal: Decimal
    notas_especiales: Optional[str] = None
    class Config:
        populate_by_name = True

# Esquema para recibir la creación de la comanda
class ComandaCreate(BaseModel):
    notas_generales: Optional[str] = None
    estado_actual: EstadoComanda = EstadoComanda.PENDIENTE
    detalles_comanda: List[DetalleCreate]
    ticket_numero: str
    total_final: Decimal
    sucursal_id: str
    notas_generales: Optional[str] = None

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