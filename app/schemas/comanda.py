import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import UUID4, BaseModel, Field, field_validator


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
    sucursal_id: uuid.UUID | None = None


# Esquema para cancelación parcial (eliminar productos de una comanda Pendiente)
class ComandaModifyRequest(BaseModel):
    detalles_ids_a_eliminar: list[str] = Field(..., min_length=1)
    motivo_cancelacion: str | None = None

    @field_validator("detalles_ids_a_eliminar")
    @classmethod
    def _validate_uuids(cls, v: list[str]) -> list[str]:
        validos: list[str] = []
        for raw in v:
            if not raw or not raw.strip():
                continue
            try:
                uuid.UUID(raw.strip())
            except ValueError as exc:
                raise ValueError(
                    f"ID de detalle inválido: '{raw}'. Se esperaba un UUID válido."
                ) from exc
            validos.append(raw.strip())
        if not validos:
            raise ValueError("No se proporcionó ningún ID de detalle válido.")
        return validos


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
