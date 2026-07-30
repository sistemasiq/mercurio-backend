from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class PadreAuthRequest(BaseModel):
    token: str


class SucursalInfo(BaseModel):
    id: UUID
    nombre: str

    model_config = ConfigDict(from_attributes=True)


class TutorInfo(BaseModel):
    id: UUID
    nombreCompleto: str  # noqa: N815
    telefono: str

    model_config = ConfigDict(from_attributes=True)


class NinoActivoResponse(BaseModel):
    id: UUID
    nombreCompleto: str  # noqa: N815
    edad: int
    estadoVisita: str  # noqa: N815
    horaEntrada: datetime | None  # noqa: N815
    horaSalidaEsperada: datetime | None  # noqa: N815
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
