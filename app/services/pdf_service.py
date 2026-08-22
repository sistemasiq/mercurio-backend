"""
app/services/pdf_service.py
Genera el comprobante PDF del arqueo de caja (tipo pre-timbrado, sin sellos fiscales)
a partir del detalle ya consolidado de un cierre_caja.
"""

from __future__ import annotations

from datetime import datetime
from io import BytesIO
from xml.sax.saxutils import escape

import pytz
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.schemas.caja import DetalleArqueoResponse

_MEXICO_TZ = pytz.timezone("America/Mexico_City")

_MARGIN = 20 * mm
_PAGE_WIDTH, _PAGE_HEIGHT = letter
_CONTENT_WIDTH = _PAGE_WIDTH - 2 * _MARGIN

_styles = getSampleStyleSheet()
_ESTILO_TITULO = ParagraphStyle("titulo", parent=_styles["Normal"], fontName="Helvetica-Bold", fontSize=16)
_ESTILO_SUBTITULO = ParagraphStyle(
    "subtitulo", parent=_styles["Normal"], fontName="Helvetica", fontSize=9, textColor=colors.grey
)
_ESTILO_SECCION = ParagraphStyle(
    "seccion", parent=_styles["Normal"], fontName="Helvetica-Bold", fontSize=12, spaceAfter=2 * mm
)
_ESTILO_LABEL = ParagraphStyle("label", parent=_styles["Normal"], fontName="Helvetica-Bold", fontSize=10)
_ESTILO_VALOR = ParagraphStyle("valor", parent=_styles["Normal"], fontName="Helvetica", fontSize=10)
_ESTILO_EXTRAORDINARIO = ParagraphStyle(
    "extraordinario", parent=_styles["Normal"], fontName="Helvetica-Bold", fontSize=11, textColor=colors.red
)
_ESTILO_OBSERVACIONES = ParagraphStyle(
    "observaciones", parent=_styles["Normal"], fontName="Helvetica", fontSize=10, leading=13
)
_ESTILO_TABLA_HEADER = ParagraphStyle(
    "tablaHeader", parent=_styles["Normal"], fontName="Helvetica-Bold", fontSize=9
)
_ESTILO_TABLA_CELDA = ParagraphStyle("tablaCelda", parent=_styles["Normal"], fontName="Helvetica", fontSize=9)
_ESTILO_TABLA_CELDA_BOLD = ParagraphStyle(
    "tablaCeldaBold", parent=_styles["Normal"], fontName="Helvetica-Bold", fontSize=9
)
_ESTILO_VACIO = ParagraphStyle("vacio", parent=_styles["Normal"], fontName="Helvetica", fontSize=9, textColor=colors.grey)
_ESTILO_TABLA_CELDA_SOBRANTE = ParagraphStyle(
    "tablaCeldaSobrante", parent=_ESTILO_TABLA_CELDA, textColor=colors.blue
)
_ESTILO_TABLA_CELDA_FALTANTE = ParagraphStyle(
    "tablaCeldaFaltante", parent=_ESTILO_TABLA_CELDA, textColor=colors.red
)
_ESTILO_TABLA_CELDA_BOLD_SOBRANTE = ParagraphStyle(
    "tablaCeldaBoldSobrante", parent=_ESTILO_TABLA_CELDA_BOLD, textColor=colors.blue
)
_ESTILO_TABLA_CELDA_BOLD_FALTANTE = ParagraphStyle(
    "tablaCeldaBoldFaltante", parent=_ESTILO_TABLA_CELDA_BOLD, textColor=colors.red
)
_ESTILO_FIRMA_LABEL = ParagraphStyle(
    "firmaLabel", parent=_styles["Normal"], fontName="Helvetica", fontSize=9, alignment=1
)


def _fmt_moneda(valor) -> str:
    return f"$ {float(valor):,.2f}"


def _celda_diferencia(valor: float, negrita: bool = False) -> Paragraph:
    """Celda de diferencia (declarado - esperado) con el mismo esquema de color
    que "Diferencia neta": rojo = faltante, azul = sobrante, negro = exacto."""
    if valor < 0:
        estilo = _ESTILO_TABLA_CELDA_BOLD_FALTANTE if negrita else _ESTILO_TABLA_CELDA_FALTANTE
        texto = f"-{_fmt_moneda(abs(valor))}"
    elif valor > 0:
        estilo = _ESTILO_TABLA_CELDA_BOLD_SOBRANTE if negrita else _ESTILO_TABLA_CELDA_SOBRANTE
        texto = f"+{_fmt_moneda(valor)}"
    else:
        estilo = _ESTILO_TABLA_CELDA_BOLD if negrita else _ESTILO_TABLA_CELDA
        texto = _fmt_moneda(0)
    return Paragraph(texto, estilo)


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


def _dibujar_pie(c, doc) -> None:
    """Pie de página fijo, fuera del área de la Frame — nunca puede ser invadido
    por el contenido dinámico porque el bottomMargin del documento ya reserva
    ese espacio (ver SimpleDocTemplate más abajo)."""
    c.saveState()
    c.setFont("Helvetica-Oblique", 8)
    c.setFillColor(colors.grey)
    c.drawString(_MARGIN, _MARGIN * 0.5, "Generado automáticamente por Mercurio — sistema de gestión de venue.")
    c.drawRightString(_PAGE_WIDTH - _MARGIN, _MARGIN * 0.5, f"Página {doc.page}")
    c.restoreState()


def _separador() -> HRFlowable:
    return HRFlowable(
        width="100%", thickness=0.75, color=colors.black, spaceBefore=3 * mm, spaceAfter=5 * mm
    )


def _tabla_datos(filas: list[tuple[str, str]]) -> Table:
    data = [[Paragraph(label, _ESTILO_LABEL), Paragraph(valor, _ESTILO_VALOR)] for label, valor in filas]
    tabla = Table(data, colWidths=[55 * mm, _CONTENT_WIDTH - 55 * mm])
    tabla.setStyle(
        TableStyle(
            [
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 1.2 * mm),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1.2 * mm),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    return tabla


def _bloque_firma(etiqueta: str, ancho: float) -> Table:
    """Espacio con línea para firmar a mano + etiqueta debajo. El TOPPADDING de la
    fila de la línea reserva el espacio físico en blanco antes del trazo."""
    tabla = Table([[""], [Paragraph(etiqueta, _ESTILO_FIRMA_LABEL)]], colWidths=[ancho])
    tabla.setStyle(
        TableStyle(
            [
                ("LINEBELOW", (0, 0), (0, 0), 0.75, colors.black),
                ("TOPPADDING", (0, 0), (0, 0), 16 * mm),
                ("BOTTOMPADDING", (0, 0), (0, 0), 1 * mm),
                ("TOPPADDING", (0, 1), (0, 1), 2 * mm),
                ("ALIGN", (0, 1), (0, 1), "CENTER"),
            ]
        )
    )
    return tabla


def _bloque_firmas(tipo_cierre: str) -> KeepTogether:
    # Cierre extraordinario se autoriza sin PIN del cajero, así que no tiene sentido
    # pedirle una firma que el flujo real nunca le exigió.
    if tipo_cierre == "EXTRAORDINARIO":
        firmas: Table | list = _bloque_firma("Firma del Administrador que autoriza", 80 * mm)
        firmas.hAlign = "CENTER"
        contenido = [firmas]
    else:
        col = _CONTENT_WIDTH / 2
        fila = Table(
            [[_bloque_firma("Firma del Cajero", col - 5 * mm), _bloque_firma("Firma del Administrador que autoriza", col - 5 * mm)]],
            colWidths=[col, col],
        )
        fila.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER"), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
        contenido = [fila]

    return KeepTogether(
        [
            Spacer(1, 4 * mm),
            _separador(),
            Paragraph("Firmas", _ESTILO_SECCION),
            Spacer(1, 2 * mm),
            *contenido,
        ]
    )


def generar_pdf_arqueo(detalle: DetalleArqueoResponse) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        topMargin=_MARGIN,
        bottomMargin=_MARGIN,
        leftMargin=_MARGIN,
        rightMargin=_MARGIN,
    )

    story: list = []

    # ── Encabezado ──────────────────────────────────────────────────────
    story.append(Paragraph("Comprobante de Cierre de Caja", _ESTILO_TITULO))
    story.append(Spacer(1, 2 * mm))
    story.append(Paragraph("Documento interno de auditoría — no válido como comprobante fiscal", _ESTILO_SUBTITULO))
    story.append(_separador())

    story.append(Paragraph(f"Folio de arqueo: {escape(detalle.id)}", _ESTILO_LABEL))
    story.append(Spacer(1, 2 * mm))

    if detalle.tipo_cierre == "EXTRAORDINARIO":
        story.append(Paragraph("⚠ CIERRE EXTRAORDINARIO — autorizado sin PIN del cajero", _ESTILO_EXTRAORDINARIO))
        story.append(Spacer(1, 2 * mm))

    # ── Datos generales ─────────────────────────────────────────────────
    story.append(
        _tabla_datos(
            [
                ("Sucursal:", escape(detalle.sucursal_nombre)),
                ("Terminal / Caja:", escape(detalle.terminal)),
                ("Cajero:", escape(detalle.cajero_nombre)),
                ("Administrador autorizante:", escape(detalle.admin_nombre or "—")),
                ("Fecha de apertura:", _fmt_fecha(detalle.fecha_apertura)),
                ("Fecha de cierre:", _fmt_fecha(detalle.fecha_cierre)),
                ("Fondo inicial:", _fmt_moneda(detalle.fondo_inicial)),
            ]
        )
    )
    story.append(_separador())

    # ── Comparativo del sistema vs. lo declarado ────────────────────────
    story.append(Paragraph("Comparativo de Caja", _ESTILO_SECCION))

    diferencia = float(detalle.diferencia_neta)
    if diferencia < 0:
        color_diferencia = colors.red
        etiqueta_diferencia = f"-{_fmt_moneda(abs(diferencia))} (faltante)"
    elif diferencia > 0:
        color_diferencia = colors.blue
        etiqueta_diferencia = f"+{_fmt_moneda(diferencia)} (sobrante)"
    else:
        color_diferencia = colors.darkgreen
        etiqueta_diferencia = "Sin diferencia — cuadre exacto"
    estilo_diferencia = ParagraphStyle(
        "diferencia", parent=_ESTILO_VALOR, fontName="Helvetica-Bold", textColor=color_diferencia
    )

    story.append(
        _tabla_datos(
            [
                ("Valor esperado (sistema):", _fmt_moneda(detalle.total_esperado)),
                ("Valor reportado (cajero):", _fmt_moneda(detalle.total_declarado)),
            ]
        )
    )
    story.append(
        Table(
            [[Paragraph("Diferencia neta:", _ESTILO_LABEL), Paragraph(etiqueta_diferencia, estilo_diferencia)]],
            colWidths=[55 * mm, _CONTENT_WIDTH - 55 * mm],
            style=TableStyle(
                [
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 1.2 * mm),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 1.2 * mm),
                ]
            ),
        )
    )
    story.append(_separador())

    # ── Desglose por método de pago ─────────────────────────────────────
    story.append(Paragraph("Desglose por Método de Pago", _ESTILO_SECCION))
    if detalle.balance_por_metodo:
        data = [
            [
                Paragraph("Método", _ESTILO_TABLA_HEADER),
                Paragraph("Esperado (sistema)", _ESTILO_TABLA_HEADER),
                Paragraph("Declarado (cajero)", _ESTILO_TABLA_HEADER),
                Paragraph("Diferencia", _ESTILO_TABLA_HEADER),
            ]
        ]
        total_esperado_metodos = 0.0
        total_declarado_metodos = 0.0
        for fila_balance in detalle.balance_por_metodo:
            data.append(
                [
                    Paragraph(escape(fila_balance.label), _ESTILO_TABLA_CELDA),
                    Paragraph(_fmt_moneda(fila_balance.esperado), _ESTILO_TABLA_CELDA),
                    Paragraph(_fmt_moneda(fila_balance.declarado), _ESTILO_TABLA_CELDA),
                    _celda_diferencia(float(fila_balance.diferencia)),
                ]
            )
            total_esperado_metodos += float(fila_balance.esperado)
            total_declarado_metodos += float(fila_balance.declarado)
        data.append(
            [
                Paragraph("Total", _ESTILO_TABLA_CELDA_BOLD),
                Paragraph(_fmt_moneda(total_esperado_metodos), _ESTILO_TABLA_CELDA_BOLD),
                Paragraph(_fmt_moneda(total_declarado_metodos), _ESTILO_TABLA_CELDA_BOLD),
                _celda_diferencia(total_declarado_metodos - total_esperado_metodos, negrita=True),
            ]
        )
        tabla_metodos = Table(
            data,
            colWidths=[_CONTENT_WIDTH * 0.3, _CONTENT_WIDTH * 0.23, _CONTENT_WIDTH * 0.23, _CONTENT_WIDTH * 0.24],
            repeatRows=1,
        )
        tabla_metodos.setStyle(
            TableStyle(
                [
                    ("LINEBELOW", (0, 0), (-1, 0), 0.75, colors.black),
                    ("LINEABOVE", (0, -1), (-1, -1), 0.75, colors.black),
                    ("TOPPADDING", (0, 0), (-1, -1), 1.5 * mm),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5 * mm),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ]
            )
        )
        story.append(tabla_metodos)
    else:
        story.append(Paragraph("Sin movimientos adicionales fuera de efectivo en este turno.", _ESTILO_VACIO))
    story.append(_separador())

    # ── Retiros parciales ────────────────────────────────────────────────
    story.append(Paragraph("Retiros Parciales", _ESTILO_SECCION))
    if detalle.retiros:
        data = [
            [
                Paragraph("Concepto", _ESTILO_TABLA_HEADER),
                Paragraph("Destinatario", _ESTILO_TABLA_HEADER),
                Paragraph("Monto", _ESTILO_TABLA_HEADER),
                Paragraph("Hora", _ESTILO_TABLA_HEADER),
            ]
        ]
        total_retiros = 0.0
        for retiro in detalle.retiros:
            data.append(
                [
                    Paragraph(escape(retiro.concepto.value), _ESTILO_TABLA_CELDA),
                    Paragraph(escape(retiro.tipo_destinatario.value), _ESTILO_TABLA_CELDA),
                    Paragraph(_fmt_moneda(retiro.monto), _ESTILO_TABLA_CELDA),
                    Paragraph(_fmt_fecha(str(retiro.creado)), _ESTILO_TABLA_CELDA),
                ]
            )
            total_retiros += float(retiro.monto)
        data.append(
            [
                "",
                "",
                Paragraph(_fmt_moneda(total_retiros), _ESTILO_TABLA_CELDA_BOLD),
                "",
            ]
        )
        tabla_retiros = Table(
            data,
            colWidths=[_CONTENT_WIDTH * 0.35, _CONTENT_WIDTH * 0.25, _CONTENT_WIDTH * 0.2, _CONTENT_WIDTH * 0.2],
            repeatRows=1,
        )
        tabla_retiros.setStyle(
            TableStyle(
                [
                    ("LINEBELOW", (0, 0), (-1, 0), 0.75, colors.black),
                    ("TOPPADDING", (0, 0), (-1, -1), 1.5 * mm),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5 * mm),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ]
            )
        )
        story.append(tabla_retiros)
    else:
        story.append(Paragraph("No se registraron retiros parciales en este turno.", _ESTILO_VACIO))
    story.append(_separador())

    # ── Observaciones ────────────────────────────────────────────────────
    story.append(Paragraph("Observaciones", _ESTILO_SECCION))
    texto_obs = escape(detalle.observaciones or "Sin observaciones registradas.")
    story.append(Paragraph(texto_obs, _ESTILO_OBSERVACIONES))

    # ── Firmas ───────────────────────────────────────────────────────────
    story.append(_bloque_firmas(detalle.tipo_cierre))

    doc.build(story, onFirstPage=_dibujar_pie, onLaterPages=_dibujar_pie)
    return buffer.getvalue()
