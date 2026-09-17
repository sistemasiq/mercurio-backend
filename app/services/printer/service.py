"""
PrinterService desacoplado con adapters GDI y PDF.
"""

from __future__ import annotations

from typing import Protocol

from app.services.printer.detection import detectar_tipo, paper_size_para_tipo
from app.services.printer.gdi_bridge import imprimir_gdi, listar_impresoras_windows
from app.services.printer.pdf_ticket import generar_pdf_base64, generar_pdf_ticket, generar_pdf_ticket_wysiwyg
import base64


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
            tipo = detectar_tipo(r.get("DriverName"), r.get("PaperNames"), r.get("Name"))
            out.append({**r, "tipo_detectado": tipo, "paper": paper_size_para_tipo(tipo)})
        return out

    async def print(self, data: dict, printer_name: str, ancho_mm: int = 58) -> dict:
        orden = data.get("orden")
        if isinstance(orden, dict) and orden.get("titulo"):
            pdf_bytes = generar_pdf_ticket_wysiwyg(orden, ancho_mm=80)
            pdf_b64 = base64.b64encode(pdf_bytes).decode("ascii")
            # Opción A: GDI texto con negritas (Consolas Bold) 1 botón, sin abrir PDF
            try:
                detalles = orden.get("detalles") or []
                lineas_gdi: list[str] = []
                bold_idx: set[int] = set()
                lineas_gdi.append("WOOW KIDS"); bold_idx.add(0)
                lineas_gdi.append("Nigromante 391, Peña | 59375 La Piedad")
                lineas_gdi.append("--------------------------------")
                lineas_gdi.append(f"TICKET: {orden.get('titulo')}  FECHA: {str(orden.get('fecha_hora') or '')[:10]}")
                for d in detalles:
                    if d.get("nombre_combo_padre"):
                        lineas_gdi.append(f"  - {d.get('cantidad')}x {d.get('producto_nombre')}")
                    else:
                        idx = len(lineas_gdi)
                        lineas_gdi.append(f"{d.get('cantidad')}x {d.get('producto_nombre')} ${float(d.get('importe') or 0):.2f}")
                        bold_idx.add(idx)
                lineas_gdi.append("--------------------------------")
                for mp in (orden.get("metodos_pago") or []):
                    lineas_gdi.append(f"PAGO {mp.get('metodo_pago_nombre')} ${float(mp.get('monto') or 0):.2f}")
                lineas_gdi.append(f"TOTAL VENTA ${float(orden.get('total_final') or 0):.2f}")
                bold_idx.add(len(lineas_gdi) - 1)
                await imprimir_gdi(printer_name, lineas_gdi, ancho_mm=80, bold_lines=bold_idx)
                return {"pdfBase64": pdf_b64, "printer": printer_name, "ancho_mm": 80}
            except Exception as e:
                import logging

                logging.getLogger(__name__).warning("GDI A falló, fallback: %s", e)
                return {"pdfBase64": pdf_b64, "printer": printer_name, "ancho_mm": 80, "fallback": True, "error": str(e)[:200]}
        lineas: list[str] = data.get("lineas") or data.get("raw_lines") or []
        if not lineas and data.get("texto"):
            lineas = str(data["texto"]).split("\n")
        if not lineas:
            lineas = ["Ticket de prueba - Woow Kids", "----------------", "Impresión OK"]
        pdf_b64 = generar_pdf_base64(lineas, ancho_mm=ancho_mm)
        await imprimir_gdi(printer_name, lineas, ancho_mm=ancho_mm)
        return {"pdfBase64": pdf_b64, "printer": printer_name, "ancho_mm": ancho_mm}

    async def preview(self, data: dict, ancho_mm: int = 58) -> bytes:
        orden = data.get("orden")
        if isinstance(orden, dict) and orden.get("titulo"):
            return generar_pdf_ticket_wysiwyg(orden, ancho_mm=80)
        lineas: list[str] = data.get("lineas") or data.get("raw_lines") or []
        if not lineas and data.get("texto"):
            lineas = str(data["texto"]).split("\n")
        if not lineas:
            lineas = ["Preview ticket", "----------------", "58mm"]
        return generar_pdf_ticket(lineas, ancho_mm=ancho_mm)


class PdfAdapter:
    """Fallback: solo PDF, sin spooler (Linux/Docker o sin driver)."""

    async def list_printers(self) -> list[dict]:
        return []

    async def print(self, data: dict, printer_name: str, ancho_mm: int = 58) -> dict:
        orden = data.get("orden")
        if isinstance(orden, dict) and orden.get("titulo"):
            pdf_bytes = generar_pdf_ticket_wysiwyg(orden, ancho_mm=80)
            pdf_b64 = base64.b64encode(pdf_bytes).decode("ascii")
            return {"pdfBase64": pdf_b64, "printer": printer_name or "PDF", "ancho_mm": 80, "fallback": True}
        lineas: list[str] = data.get("lineas") or data.get("raw_lines") or []
        if not lineas and data.get("texto"):
            lineas = str(data["texto"]).split("\n")
        if not lineas:
            lineas = ["Ticket de prueba - Woow Kids (PDF)", "----------------", f"Ancho {ancho_mm}mm"]
        pdf_b64 = generar_pdf_base64(lineas, ancho_mm=ancho_mm)
        return {"pdfBase64": pdf_b64, "printer": printer_name or "PDF", "ancho_mm": ancho_mm, "fallback": True}

    async def preview(self, data: dict, ancho_mm: int = 58) -> bytes:
        orden = data.get("orden")
        if isinstance(orden, dict) and orden.get("titulo"):
            return generar_pdf_ticket_wysiwyg(orden, ancho_mm=80)
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
