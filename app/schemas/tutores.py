from pydantic import BaseModel


class TutorIn(BaseModel):
    nombreCompleto: str  # noqa: N815 — camelCase requerido por el contrato JSON del frontend
    telefono: str
