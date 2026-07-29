"""
app/services/pdf_service.py
Genera el comprobante PDF del arqueo de caja (tipo pre-timbrado, sin sellos fiscales)
a partir del detalle ya consolidado de un cierre_caja.
"""

from __future__ import annotations

from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from app.schemas.caja import DetalleArqueoResponse


def _fmt_moneda(valor) -> str:
    return f"$ {float(valor):,.2f}"


def _fmt_fecha(valor: str) -> str:
    # Los timestamps llegan como string "YYYY-MM-DD HH:MM:SS.ffffff+00:00" desde asyncpg/str()
    return valor.split(".")[0].replace("T", " ") if valor else "—"


def generar_pdf_arqueo(detalle: DetalleArqueoResponse) -> bytes:
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    margin = 20 * mm
    y = height - margin

    # ── Encabezado ──────────────────────────────────────────────────────
    c.setFont("Helvetica-Bold", 16)
    c.drawString(margin, y, "Comprobante de Cierre de Caja")
    y -= 6 * mm
    c.setFont("Helvetica", 9)
    c.setFillColor(colors.grey)
    c.drawString(margin, y, "Documento interno de auditoría — no válido como comprobante fiscal")
    c.setFillColor(colors.black)
    y -= 4 * mm
    c.line(margin, y, width - margin, y)
    y -= 8 * mm

    c.setFont("Helvetica-Bold", 11)
    c.drawString(margin, y, f"Folio de arqueo: {detalle.id}")
    y -= 7 * mm

    if detalle.tipo_cierre == "EXTRAORDINARIO":
        c.setFont("Helvetica-Bold", 11)
        c.setFillColor(colors.red)
        c.drawString(margin, y, "⚠ CIERRE EXTRAORDINARIO — autorizado sin PIN del cajero")
        c.setFillColor(colors.black)
        y -= 7 * mm

    y -= 3 * mm

    # ── Datos generales ─────────────────────────────────────────────────
    def fila(label: str, valor: str) -> None:
        nonlocal y
        c.setFont("Helvetica-Bold", 10)
        c.drawString(margin, y, label)
        c.setFont("Helvetica", 10)
        c.drawString(margin + 55 * mm, y, valor)
        y -= 7 * mm

    fila("Sucursal:", detalle.sucursal_nombre)
    fila("Terminal / Caja:", detalle.terminal)
    fila("Cajero:", detalle.cajero_nombre)
    fila("Administrador autorizante:", detalle.admin_nombre or "—")
    fila("Fecha de apertura:", _fmt_fecha(detalle.fecha_apertura))
    fila("Fecha de cierre:", _fmt_fecha(detalle.fecha_cierre))
    fila("Fondo inicial:", _fmt_moneda(detalle.fondo_inicial))

    y -= 4 * mm
    c.line(margin, y, width - margin, y)
    y -= 10 * mm

    # ── Comparativo del sistema vs. lo declarado ────────────────────────
    c.setFont("Helvetica-Bold", 12)
    c.drawString(margin, y, "Comparativo de Caja")
    y -= 9 * mm

    fila("Valor esperado (sistema):", _fmt_moneda(detalle.total_esperado))
    fila("Valor reportado (cajero):", _fmt_moneda(detalle.total_declarado))

    diferencia = float(detalle.diferencia_neta)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(margin, y, "Diferencia neta:")
    c.setFont("Helvetica-Bold", 10)
    if diferencia < 0:
        c.setFillColor(colors.red)
        etiqueta = f"-{_fmt_moneda(abs(diferencia))} (faltante)"
    elif diferencia > 0:
        c.setFillColor(colors.blue)
        etiqueta = f"+{_fmt_moneda(diferencia)} (sobrante)"
    else:
        c.setFillColor(colors.darkgreen)
        etiqueta = "Sin diferencia — cuadre exacto"
    c.drawString(margin + 55 * mm, y, etiqueta)
    c.setFillColor(colors.black)
    y -= 10 * mm

    c.line(margin, y, width - margin, y)
    y -= 10 * mm

    # ── Observaciones ────────────────────────────────────────────────────
    c.setFont("Helvetica-Bold", 12)
    c.drawString(margin, y, "Observaciones")
    y -= 8 * mm
    c.setFont("Helvetica", 10)
    texto_obs = detalle.observaciones or "Sin observaciones registradas."
    max_chars_linea = 95
    for i in range(0, len(texto_obs), max_chars_linea):
        c.drawString(margin, y, texto_obs[i : i + max_chars_linea])
        y -= 6 * mm

    # ── Pie ──────────────────────────────────────────────────────────────
    c.setFont("Helvetica-Oblique", 8)
    c.setFillColor(colors.grey)
    c.drawString(margin, margin, "Generado automáticamente por Mercurio — sistema de gestión de venue.")

    c.showPage()
    c.save()
    return buffer.getvalue()
