from pydantic import BaseModel, Field


class NinoIn(BaseModel):
    nombreCompleto: str  # noqa: N815 — camelCase requerido por el contrato JSON del frontend
    edad: int = Field(ge=1, le=99)
    notas: str | None = None
