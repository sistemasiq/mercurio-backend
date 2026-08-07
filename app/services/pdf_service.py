"""
app/services/pdf_service.py
Genera el comprobante PDF del arqueo de caja (tipo pre-timbrado, sin sellos fiscales)
a partir del detalle ya consolidado de un cierre_caja.
"""

from __future__ import annotations

from datetime import datetime
from io import BytesIO

import pytz
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from app.schemas.caja import DetalleArqueoResponse

_MEXICO_TZ = pytz.timezone("America/Mexico_City")


def _fmt_moneda(valor) -> str:
    return f"$ {float(valor):,.2f}"


def _fmt_fecha(valor: str) -> str:
    # Los timestamps llegan como string "YYYY-MM-DD HH:MM:SS.ffffff+00:00" (UTC) desde
    # asyncpg/str(). Antes solo se recortaban los microsegundos sin convertir de zona
    # horaria, así que el PDF mostraba la hora en UTC en vez de hora de México — 6 horas
    # adelantada respecto a la tabla de arqueos (que sí convierte al renderizar en el navegador).
    if not valor:
        return "—"
    dt = datetime.fromisoformat(valor)
    if dt.tzinfo is None:
        dt = pytz.utc.localize(dt)
    return dt.astimezone(_MEXICO_TZ).strftime("%Y-%m-%d %H:%M:%S")


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

    # ── Desglose por método de pago ─────────────────────────────────────
    c.setFont("Helvetica-Bold", 12)
    c.drawString(margin, y, "Desglose por Método de Pago")
    y -= 9 * mm

    if detalle.balance_por_metodo:
        c.setFont("Helvetica-Bold", 9)
        c.drawString(margin, y, "Método")
        c.drawString(margin + 70 * mm, y, "Esperado (sistema)")
        c.drawString(margin + 115 * mm, y, "Declarado (cajero)")
        y -= 6 * mm
        c.setFont("Helvetica", 9)
        for fila_balance in detalle.balance_por_metodo:
            c.drawString(margin, y, fila_balance.label)
            c.drawString(margin + 70 * mm, y, _fmt_moneda(fila_balance.esperado))
            c.drawString(margin + 115 * mm, y, _fmt_moneda(fila_balance.declarado))
            y -= 6 * mm
    else:
        c.setFont("Helvetica", 9)
        c.setFillColor(colors.grey)
        c.drawString(margin, y, "Sin movimientos adicionales fuera de efectivo en este turno.")
        c.setFillColor(colors.black)
        y -= 6 * mm

    y -= 4 * mm
    c.line(margin, y, width - margin, y)
    y -= 10 * mm

    # ── Retiros parciales ────────────────────────────────────────────────
    c.setFont("Helvetica-Bold", 12)
    c.drawString(margin, y, "Retiros Parciales")
    y -= 9 * mm

    if detalle.retiros:
        c.setFont("Helvetica-Bold", 9)
        c.drawString(margin, y, "Concepto")
        c.drawString(margin + 60 * mm, y, "Destinatario")
        c.drawString(margin + 100 * mm, y, "Monto")
        c.drawString(margin + 130 * mm, y, "Hora")
        y -= 6 * mm
        c.setFont("Helvetica", 9)
        total_retiros = 0.0
        for retiro in detalle.retiros:
            c.drawString(margin, y, retiro.concepto.value)
            c.drawString(margin + 60 * mm, y, retiro.tipo_destinatario.value)
            c.drawString(margin + 100 * mm, y, _fmt_moneda(retiro.monto))
            c.drawString(margin + 130 * mm, y, _fmt_fecha(str(retiro.creado)))
            total_retiros += float(retiro.monto)
            y -= 6 * mm
        c.setFont("Helvetica-Bold", 9)
        c.drawString(margin + 100 * mm, y, _fmt_moneda(total_retiros))
        y -= 6 * mm
    else:
        c.setFont("Helvetica", 9)
        c.setFillColor(colors.grey)
        c.drawString(margin, y, "No se registraron retiros parciales en este turno.")
        c.setFillColor(colors.black)
        y -= 6 * mm

    y -= 4 * mm
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
