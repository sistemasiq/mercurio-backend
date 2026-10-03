from __future__ import annotations

from datetime import datetime, time
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field, StringConstraints, model_validator

NombreRequerido = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
TelefonoOpcional = Annotated[str, StringConstraints(strip_whitespace=True, max_length=20)] | None


def _validar_horario(hora_apertura: time, hora_cierre: time) -> None:
    """No se soporta cruce de medianoche: la apertura debe ser menor que el
    cierre."""
    if hora_apertura >= hora_cierre:
        raise ValueError("hora_apertura debe ser menor que hora_cierre")


class BranchCreateRequest(BaseModel):
    nombre: NombreRequerido
    direccion: str | None = None
    ciudad: str | None = None
    estado: str | None = None
    codigo_postal: str | None = Field(default=None, max_length=10)
    zona_horaria: str = Field(default="America/Mexico_City")
    hora_apertura: time = Field(default=time(9, 0))
    hora_cierre: time = Field(default=time(23, 0))
    telefono: TelefonoOpcional = Field(default=None)
    correo: str | None = None
    administrador_id: UUID | None = None
    clave: str | None = None

    @model_validator(mode="after")
    def _validar(self) -> BranchCreateRequest:
        _validar_horario(self.hora_apertura, self.hora_cierre)
        return self


class BranchUpdateRequest(BaseModel):
    nombre: NombreRequerido
    direccion: str | None = None
    ciudad: str | None = None
    estado: str | None = None
    codigo_postal: str | None = Field(default=None, max_length=10)
    zona_horaria: str = Field(default="America/Mexico_City")
    hora_apertura: time = Field(default=time(9, 0))
    hora_cierre: time = Field(default=time(23, 0))
    telefono: TelefonoOpcional = Field(default=None)
    correo: str | None = None
    administrador_id: UUID | None = None
    clave: str | None = None

    @model_validator(mode="after")
    def _validar(self) -> BranchUpdateRequest:
        _validar_horario(self.hora_apertura, self.hora_cierre)
        return self


class BranchResponse(BaseModel):
    id: UUID
    nombre: str
    direccion: str | None
    ciudad: str | None = None
    estado: str | None = None
    codigo_postal: str | None = None
    zona_horaria: str = "America/Mexico_City"
    hora_apertura: time = time(9, 0)
    hora_cierre: time = time(23, 0)
    telefono: str | None
    correo: str | None
    administrador_id: UUID | None
    administrador_name: str | None
    clave: str | None
    is_active: bool
    creado: datetime | None = None
    creado_por: UUID | None = None
    creador_name: str | None = None
    modificado: datetime | None = None
    modificado_por: UUID | None = None
    modificador_name: str | None = None


class IndicadoresSucursalResponse(BaseModel):
    """Indicadores de solo lectura de una sucursal en un periodo.

    `cajas_abiertas` es una foto del momento (no depende de desde/hasta):
    cuántas cajas de la sucursal tienen un turno abierto ahora mismo.
    """

    ventas: Decimal
    ninos_atendidos: int
    eventos: int
    cajas_abiertas: int
