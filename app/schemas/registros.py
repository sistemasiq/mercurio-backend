from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.ninos import NinoIn
from app.schemas.pagos import PagoIn
from app.schemas.tutores import TutorIn


class DetalleIn(BaseModel):
    nino: NinoIn
    productoId: UUID  # noqa: N815 — camelCase requerido por el contrato JSON del frontend
    cantidad: int = Field(gt=0)
    pulseraId: UUID  # noqa: N815 — camelCase requerido por el contrato JSON del frontend


class OnboardingRequest(BaseModel):
    sucursalId: UUID  # noqa: N815 — camelCase requerido por el contrato JSON del frontend
    tutor: TutorIn
    parentesco: str
    detalles: list[DetalleIn]
    pagos: list[PagoIn]


class OnboardingResponse(BaseModel):
    registroId: UUID  # noqa: N815 — camelCase requerido por el contrato JSON del frontend
    total: float
    pagado: float
    estado: str


class CheckoutResponse(BaseModel):
    detalleId: str  # noqa: N815 — camelCase requerido por el contrato JSON del frontend
    registroId: str  # noqa: N815 — camelCase requerido por el contrato JSON del frontend
    horasExtra: int  # noqa: N815 — camelCase requerido por el contrato JSON del frontend
    totalExtra: float  # noqa: N815 — camelCase requerido por el contrato JSON del frontend
    ninosRestantes: int  # noqa: N815 — camelCase requerido por el contrato JSON del frontend


class ProductoResponse(BaseModel):
    id: UUID
    nombre: str
    precio_unitario: float
    descripcion: str | None


class DetalleActivoResponse(BaseModel):
    registro_id: UUID
    detalle_id: UUID
    nino: str
    notas: str | None
    edad: int
    tutor: str
    telefono: str
    parentesco: str
    pulsera: str
    minutos_pagados: float
    minutos_transcurridos: float
