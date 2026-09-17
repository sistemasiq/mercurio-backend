from __future__ import annotations

from pydantic import BaseModel, Field


class PrinterMeta(BaseModel):
    Name: str = Field(description="Nombre exacto como aparece en Windows")
    DriverName: str = ""
    PortName: str = ""
    PaperNames: list[str] = Field(default_factory=list)
    tipo_detectado: str = "desconocida"
    paper: dict | None = None


class PrinterConfigPayload(BaseModel):
    tipo: str = Field(pattern="^(ticket|etiqueta)$", description="ticket|etiqueta")
    nombre_impresora: str = Field(min_length=1)
    ancho_mm: int | None = Field(default=None, description="58|80|60")
    alto_mm: int | None = None
    tipo_detectado: str | None = None
    override_manual: bool = False


class PrinterFormatoPayload(BaseModel):
    tipo: str = Field(default="ticket", pattern="^(ticket|etiqueta)$", description="ticket|etiqueta")
    ancho_mm: int = Field(description="58|80|60|210")
    alto_mm: int | None = None


class PrinterConfigResponse(BaseModel):
    id: str
    sucursal_id: str
    tipo: str
    nombre_impresora: str
    ancho_mm: int
    alto_mm: int | None
    driver_detectado: str | None
    tipo_detectado: str
    paper_names: list[str] = Field(default_factory=list)
    override_manual: bool


class PrintTicketPayload(BaseModel):
    printerName: str | None = None
    tipo: str | None = Field(default="ticket", pattern="^(ticket|etiqueta)$")
    ancho_mm: int | None = None
    lineas: list[str] | None = None
    texto: str | None = None
    data: dict | None = None  # alias genérico


class PrintTicketResponse(BaseModel):
    pdfBase64: str
    printer: str
    ancho_mm: int
    fallback: bool = False
