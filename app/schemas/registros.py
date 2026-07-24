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
    nombreSegundoTutor: str | None = None  # noqa: N815 — camelCase requerido por el contrato JSON del frontend
    pulseraTutorId: UUID  # noqa: N815 — camelCase requerido por el contrato JSON del frontend
    parentesco: str
    detalles: list[DetalleIn]
    pagos: list[PagoIn]


class OnboardingResponse(BaseModel):
    registroId: UUID  # noqa: N815 — camelCase requerido por el contrato JSON del frontend
    total: float
    pagado: float
    estado: str


class CheckoutRequest(BaseModel):
    pulseraTutorId: UUID  # noqa: N815 — camelCase requerido por el contrato JSON del frontend


class CheckoutResponse(BaseModel):
    detalleId: str  # noqa: N815 — camelCase requerido por el contrato JSON del frontend
    registroId: str  # noqa: N815 — camelCase requerido por el contrato JSON del frontend
    horasExtra: int  # noqa: N815 — camelCase requerido por el contrato JSON del frontend
    totalExtra: float  # noqa: N815 — camelCase requerido por el contrato JSON del frontend
    ninosRestantes: int  # noqa: N815 — camelCase requerido por el contrato JSON del frontend


class ProductoResponse(BaseModel):
    id: UUID
    nombre: str
    precioUnitario: float  # noqa: N815 — camelCase requerido por el contrato JSON del frontend
    descripcion: str | None


class DetalleActivoResponse(BaseModel):
    registroId: UUID  # noqa: N815 — camelCase requerido por el contrato JSON del frontend
    nombreSegundoTutor: str | None = None  # noqa: N815 — camelCase requerido por el contrato JSON del frontend
    pulseraTutorId: UUID  # noqa: N815 — camelCase requerido por el contrato JSON del frontend
    pulseraTutorRfid: str  # noqa: N815 — camelCase requerido por el contrato JSON del frontend
    detalleId: UUID  # noqa: N815 — camelCase requerido por el contrato JSON del frontend
    nino: str
    notas: str | None
    edad: int
    tutor: str
    telefono: str
    parentesco: str
    pulsera: str
    minutosPagados: float  # noqa: N815 — camelCase requerido por el contrato JSON del frontend
    minutosTranscurridos: float  # noqa: N815 — camelCase requerido por el contrato JSON del frontend
