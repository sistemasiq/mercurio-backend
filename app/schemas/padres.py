from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class PadreAuthRequest(BaseModel):
    code: str


class SucursalInfo(BaseModel):
    id: UUID
    nombre: str

    model_config = ConfigDict(from_attributes=True)


class TutorInfo(BaseModel):
    id: UUID
    nombreCompleto: str  # noqa: N815
    telefono: str
    sucursal: SucursalInfo


class NinoActivoResponse(BaseModel):
    id: UUID
    nombreCompleto: str  # noqa: N815
    edad: int
    estadoVisita: str  # noqa: N815
    horaEntrada: datetime | None  # noqa: N815
    horaSalidaEsperada: datetime | None  # noqa: N815
    horaSalida: datetime | None  # noqa: N815
    minutosTranscurridos: int  # noqa: N815
    minutosPagados: int  # noqa: N815
    pulsera: str | None
    # Solo si la visita sigue activa: excedente estimado en este momento, con
    # la misma fórmula que la cotización del checkout (ver chekouts.py).
    cargoExtra: float = 0.0  # noqa: N815
    # Solo si la visita ya terminó: lo que costó esta estancia (tiempo
    # contratado + cualquier cargo extra ya cobrado) y los puntos de lealtad
    # otorgados por el registro completo (el programa otorga por registro,
    # no por niño, así que todos los hermanos de un mismo registro ven el
    # mismo valor aquí).
    importe: float | None = None
    puntosGanados: int | None = None  # noqa: N815

    model_config = ConfigDict(from_attributes=True)


class PadreDashboardResponse(BaseModel):
    token: str
    token_type: str = "Bearer"
    expires_in: int
    tutor: TutorInfo
    ninosActivos: list[NinoActivoResponse]  # noqa: N815


class PadreNinosActivosResponse(BaseModel):
    """QA #31 — respuesta del polling autenticado con el token de `/padres/auth`
    (Authorization: Bearer), sin volver a mandar el código."""

    ninosActivos: list[NinoActivoResponse]  # noqa: N815
