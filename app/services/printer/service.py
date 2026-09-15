"""
PrinterService desacoplado con adapters GDI y PDF.
"""

from __future__ import annotations

from typing import Protocol

from app.services.printer.detection import detectar_tipo, paper_size_para_tipo
from app.services.printer.gdi_bridge import imprimir_gdi, listar_impresoras_windows
from app.services.printer.pdf_ticket import generar_pdf_base64, generar_pdf_ticket


class PrinterAdapter(Protocol):
    async def list_printers(self) -> list[dict]: ...
    async def print(self, data: dict, printer_name: str, ancho_mm: int = 58) -> dict: ...
    async def preview(self, data: dict, ancho_mm: int = 58) -> bytes: ...


class GdiAdapter:
    """Adapter GDI (Windows). Usa System.Drawing.Printing.PrintDocument."""

    async def list_printers(self) -> list[dict]:
        raw = await listar_impresoras_windows()
        out = []
        for r in raw:
            tipo = detectar_tipo(r.get("DriverName"), r.get("PaperNames"))
            out.append({**r, "tipo_detectado": tipo, "paper": paper_size_para_tipo(tipo)})
        return out

    async def print(self, data: dict, printer_name: str, ancho_mm: int = 58) -> dict:
        lineas: list[str] = data.get("lineas") or data.get("raw_lines") or []
        if not lineas and data.get("texto"):
            lineas = str(data["texto"]).split("\n")
        if not lineas:
            lineas = ["Ticket de prueba - Woow Kids", "----------------", "Impresión OK"]
        # Generar PDF para preview también
        pdf_b64 = generar_pdf_base64(lineas, ancho_mm=ancho_mm)
        # Enviar a spooler GDI (silencioso)
        await imprimir_gdi(printer_name, lineas, ancho_mm=ancho_mm)
        return {"pdfBase64": pdf_b64, "printer": printer_name, "ancho_mm": ancho_mm}

    async def preview(self, data: dict, ancho_mm: int = 58) -> bytes:
        lineas: list[str] = data.get("lineas") or data.get("raw_lines") or []
        if not lineas and data.get("texto"):
            lineas = str(data["texto"]).split("\n")
        if not lineas:
            lineas = ["Preview ticket", "----------------", "58mm"]
        return generar_pdf_ticket(lineas, ancho_mm=ancho_mm)


class PdfAdapter:
    """Fallback: solo PDF, sin spooler (Linux/Docker o sin driver)."""

    async def list_printers(self) -> list[dict]:
        # En no-Windows no hay impresoras GDI; dejar que frontend use window.print()
        return []

    async def print(self, data: dict, printer_name: str, ancho_mm: int = 58) -> dict:
        lineas: list[str] = data.get("lineas") or data.get("raw_lines") or []
        if not lineas and data.get("texto"):
            lineas = str(data["texto"]).split("\n")
        if not lineas:
            lineas = ["Ticket de prueba - Woow Kids (PDF)", "----------------", f"Ancho {ancho_mm}mm"]
        pdf_b64 = generar_pdf_base64(lineas, ancho_mm=ancho_mm)
        return {"pdfBase64": pdf_b64, "printer": printer_name or "PDF", "ancho_mm": ancho_mm, "fallback": True}

    async def preview(self, data: dict, ancho_mm: int = 58) -> bytes:
        lineas: list[str] = data.get("lineas") or data.get("raw_lines") or []
        if not lineas and data.get("texto"):
            lineas = str(data["texto"]).split("\n")
        if not lineas:
            lineas = ["Preview ticket PDF", "----------------", f"{ancho_mm}mm"]
        return generar_pdf_ticket(lineas, ancho_mm=ancho_mm)


class PrinterService:
    def __init__(self, adapter: PrinterAdapter):
        self.adapter = adapter

    async def list_printers(self) -> list[dict]:
        return await self.adapter.list_printers()

    async def print(self, data: dict, printer_name: str, ancho_mm: int = 58) -> dict:
        return await self.adapter.print(data, printer_name, ancho_mm)

    async def preview(self, data: dict, ancho_mm: int = 58) -> bytes:
        return await self.adapter.preview(data, ancho_mm)


def get_printer_service() -> PrinterService:
    import platform

    if platform.system() == "Windows":
        return PrinterService(GdiAdapter())
    return PrinterService(PdfAdapter())
