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


class LealtadPadreInfo(BaseModel):
    """WP B4, pendiente 5: saldo de puntos de lealtad del tutor, mostrado en
    la tarjeta "Tus puntos Woow" del dashboard del portal de padres."""

    saldo: int
    por_vencer: int = 0


class TutorInfo(BaseModel):
    id: UUID
    nombreCompleto: str  # noqa: N815
    telefono: str
    sucursal: SucursalInfo
    lealtad: LealtadPadreInfo | None = None


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
