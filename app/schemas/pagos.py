from uuid import UUID

from pydantic import BaseModel


class PagoIn(BaseModel):
    metodoPagoId: UUID  # noqa: N815 — camelCase requerido por el contrato JSON del frontend
    monto: float
