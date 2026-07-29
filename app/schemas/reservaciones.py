from datetime import date, datetime, time
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class ReservacionesBase(BaseModel):
    sucursal_id: UUID
    tipo_evento_id: UUID
    paquete_id: UUID
    nombre_cliente: str = Field(..., max_length=150)
    apellidos_cliente: str | None = Field(None, max_length=150)
    telefono_cliente: str = Field(..., max_length=10, pattern=r"^\d{10}$")
    email_cliente: str | None = Field(None, max_length=150)
    notas_cliente: str | None = None
    nombre_festejado: str | None = Field(None, max_length=150)
    edad_festejado: int | None = None
    fecha_evento: date
    hora_inicio: time
    hora_fin: time
    numero_personas: int = Field(..., gt=0)
    precio_base: Decimal
    precio_personas_extra: Decimal = Field(Decimal(0), ge=0)
    precio_extras: Decimal = Field(Decimal(0), ge=0)
    descuento: Decimal = Field(Decimal(0), ge=0)
    precio_total: Decimal
    anticipo: Decimal = Field(Decimal(0), ge=0)
    estado: Literal["pendiente", "confirmada", "en_curso", "completada", "cancelada"] = "pendiente"
    notas: str | None = None

    @model_validator(mode="after")
    def validar_horario(self) -> "ReservacionesBase":
        if self.hora_fin <= self.hora_inicio:
            raise ValueError("hora_fin debe ser mayor a hora_inicio")
        return self


class ReservacionesCrear(ReservacionesBase):
    pass


class ReservacionesUpdate(BaseModel):
    nombre_cliente: str | None = Field(None, max_length=150)
    apellidos_cliente: str | None = Field(None, max_length=150)
    telefono_cliente: str | None = Field(None, max_length=10, pattern=r"^\d{10}$")
    email_cliente: str | None = None
    notas_cliente: str | None = None
    nombre_festejado: str | None = None
    edad_festejado: int | None = None
    fecha_evento: date | None = None
    hora_inicio: time | None = None
    hora_fin: time | None = None
    numero_personas: int | None = Field(None, gt=0)
    precio_base: Decimal | None = None
    precio_personas_extra: Decimal | None = None
    precio_extras: Decimal | None = None
    descuento: Decimal | None = None
    precio_total: Decimal | None = None
    anticipo: Decimal | None = None
    estado: Literal["pendiente", "confirmada", "en_curso", "completada", "cancelada"] | None = None
    notas: str | None = None
    activo: bool | None = None

    @model_validator(mode="after")
    def validar_horario(self) -> "ReservacionesUpdate":
        if self.hora_inicio is None or self.hora_fin is None:
            return self
        if self.hora_fin <= self.hora_inicio:
            raise ValueError("hora_fin debe ser mayor a hora_inicio")
        return self


class ReservacionesOut(ReservacionesBase):
    id: UUID
    saldo_pendiente: Decimal
    activo: bool
    creado: datetime
    creado_por: UUID | None
    modificado: datetime | None
    modificado_por: UUID | None

    model_config = {"from_attributes": True}


class EventoDelDiaOut(BaseModel):
    id: UUID
    nombre_cliente: str
    apellidos_cliente: str | None
    telefono_cliente: str
    hora_inicio: time
    hora_fin: time
    numero_personas: int
    fecha_evento: date
 
    model_config = {"from_attributes": True}

