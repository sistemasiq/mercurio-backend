"""
Generación PDF térmico 58/80mm y etiqueta 60x40 con reportlab.
"""

from __future__ import annotations

import base64
import textwrap
from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

# 58mm = 164.4pt, 80mm = 226.77pt
_ANCHO_PT = {58: 58 * mm, 80: 80 * mm, 60: 60 * mm}
_ALTO_ETIQUETA_PT = 40 * mm


def formatear_lineas_ticket(
    encabezado: str | None = None,
    lineas_items: list[dict] | None = None,
    total: str | None = None,
    pie: str | None = None,
    ancho_chars: int | None = None,
    raw_lines: list[str] | None = None,
) -> list[str]:
    """Si se pasan raw_lines, se usan tal cual. Si no, construye desde estructura."""
    if raw_lines is not None:
        return raw_lines
    out: list[str] = []
    if encabezado:
        for ln in encabezado.split("\n"):
            out.extend(textwrap.wrap(ln, width=ancho_chars or 32) or [""])
    if lineas_items:
        for it in lineas_items:
            nombre = str(it.get("nombre", ""))[:20]
            cant = str(it.get("cantidad", ""))
            precio = str(it.get("precio", ""))
            # 32 chars: "Nombre           1 x $10.00"
            filler = max(1, (ancho_chars or 32) - len(nombre) - len(cant) - len(precio) - 4)
            out.append(f"{nombre}{' ' * filler}{cant} x {precio}")
    if total:
        out.append("-" * (ancho_chars or 32))
        out.append(total.rjust(ancho_chars or 32))
    if pie:
        out.append("")
        for ln in pie.split("\n"):
            out.extend(textwrap.wrap(ln, width=ancho_chars or 32) or [""])
    return out


def generar_pdf_ticket(
    lineas: list[str],
    ancho_mm: int = 58,
    alto_mm: int | None = None,
    font_name: str = "Courier",
    font_size: float = 7.5,
    titulo: str | None = None,
) -> bytes:
    ancho_pt = _ANCHO_PT.get(ancho_mm, 58 * mm)
    # alto dinámico: 10mm por línea + márgenes
    line_h = font_size * 1.35
    alto_pt = alto_mm * mm if alto_mm else (max(40, len(lineas) * line_h + 30))
    # Para ticket sin alto fijo, usamos alto dinámico; para etiqueta 60x40, fijo
    if ancho_mm == 60 and (alto_mm == 40 or alto_mm is None):
        alto_pt = _ALTO_ETIQUETA_PT
        ancho_pt = 60 * mm

    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=(ancho_pt, alto_pt))
    c.setFont(font_name, font_size)

    x = 4 * mm if ancho_mm != 60 else 3 * mm
    y = alto_pt - 6 * mm
    if titulo:
        c.setFont(f"{font_name}-Bold", font_size + 1)
        c.drawCentredString(ancho_pt / 2, y, titulo[:32])
        y -= line_h + 2
        c.setFont(font_name, font_size)

    for ln in lineas:
        # truncar a ancho chars aproximado
        c.drawString(x, y, ln[:64])
        y -= line_h
        if y < 4 * mm:
            break

    c.showPage()
    c.save()
    return buf.getvalue()


def generar_pdf_ticket_wysiwyg(
    orden: dict,
    ancho_mm: int = 80,
) -> bytes:
    """PDF WYSIWYG dinámico — respeta diseno JSON y ancho 58/80."""
    from reportlab.lib.colors import HexColor

    import logging

    log = logging.getLogger(__name__)
    log.info("WYSIWYG orden titulo=%s detalles=%s metodos=%s", orden.get("titulo"), len(orden.get("detalles") or []), len(orden.get("metodos_pago") or []))

    # Diseño fijo WOOW KIDS — se mantiene simple como pidió el usuario
    hdr_titulo = "WOOW KIDS"
    hdr_l1 = "Nigromante 391, Peña"
    hdr_l2 = "59375 La Piedad de Cabadas, Michoacán."
    foot_l1 = "*** GRACIAS POR SU COMPRA ***"
    foot_l2 = "ESTE NO ES UN COMPROBANTE FISCAL"
    mostrar_footer = True
    label_total = "TOTAL VENTA"

    # ancho y escala 58mm más pequeño
    if ancho_mm not in (58, 80, 60, 210):
        ancho_mm = 80
    is_narrow = ancho_mm == 58
    scale = 0.85 if is_narrow else 1.0
    margin = 3 * mm if is_narrow else 4 * mm
    ancho_pt = ancho_mm * mm
    detalles = orden.get("detalles") or []
    principales = [d for d in detalles if not d.get("nombre_combo_padre")]
    hijos = [d for d in detalles if d.get("nombre_combo_padre")]
    filas: list[dict] = []
    for p in principales:
        filas.append(p)
        filas.extend([h for h in hijos if h.get("nombre_combo_padre") == p.get("producto_nombre")])

    alto_pt = 28 * mm + len(filas) * 5 * mm + len(orden.get("metodos_pago") or []) * 5 * mm + 38 * mm
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=(ancho_pt, alto_pt))

    def draw_centered(text: str, y: float, size: float = 7, bold: bool = False):
        c.setFont("Helvetica-Bold" if bold else "Helvetica", size * scale)
        c.drawCentredString(ancho_pt / 2, y, text[:48])

    def draw_text(text: str, x: float, y: float, size: float = 7, bold: bool = False):
        c.setFont("Helvetica-Bold" if bold else "Helvetica", size * scale)
        c.drawString(x, y, text[:64])

    def draw_dashed(y: float):
        c.setDash(2, 2)
        c.setStrokeColor(HexColor(0x000000))
        c.line(margin, y, ancho_pt - margin, y)
        c.setDash()

    def draw_line(y: float):
        c.setStrokeColor(HexColor(0x000000))
        c.line(margin, y, ancho_pt - margin, y)

    y = alto_pt - 8 * mm
    draw_centered(hdr_titulo, y, size=11, bold=True)
    y -= 5 * mm
    draw_centered(hdr_l1, y, size=6)
    y -= 3.5 * mm
    draw_centered(hdr_l2, y, size=6)
    y -= 5 * mm
    draw_dashed(y)
    y -= 5 * mm

    fecha_raw = orden.get("fecha_hora") or ""
    try:
        from datetime import datetime

        d = datetime.fromisoformat(fecha_raw.replace("Z", "+00:00"))
        fecha_str = d.strftime("%d %b %Y")
        hora_str = d.strftime("%I:%M %p")
    except:
        fecha_str = str(fecha_raw)[:10]
        hora_str = ""

    titulo = orden.get("titulo") or orden.get("ticket_numero") or ""
    col_desc_x = 12 * mm if is_narrow else 16 * mm
    col_imp_off = 12 * mm if is_narrow else 14 * mm
    fecha_off = 24 * mm if is_narrow else 28 * mm
    draw_text(f"TICKET: {titulo}", margin, y, size=6, bold=True)
    draw_text(f"FECHA: {fecha_str}", ancho_pt - fecha_off, y, size=6, bold=True)
    y -= 4 * mm
    draw_text(f"CAJERO: {(orden.get('creado_por_nombre') or 'N/A').split(' ')[0]}", margin, y, size=6, bold=True)
    draw_text(f"HORA: {hora_str}", ancho_pt - fecha_off, y, size=6, bold=True)
    y -= 4 * mm
    if orden.get("nombre_cliente"):
        draw_text(f"CLIENTE: {orden.get('nombre_cliente')}", margin, y, size=6)
        y -= 4 * mm
    y -= 1 * mm
    draw_dashed(y)
    y -= 5 * mm

    draw_text("CANT", margin, y, size=6, bold=True)
    draw_text("DESCRIPCIÓN", col_desc_x, y, size=6, bold=True)
    draw_text("Importe", ancho_pt - col_imp_off, y, size=6, bold=True)
    y -= 3 * mm
    draw_line(y)
    y -= 5 * mm

    for item in filas:
        if item.get("nombre_combo_padre"):
            draw_text(f"  - {item.get('cantidad')}x {item.get('producto_nombre')}", col_desc_x, y, size=6)
            y -= 4 * mm
            continue
        cant = str(item.get("cantidad") or "")
        max_n = 20 if is_narrow else 28
        nombre = str(item.get("producto_nombre") or "")[:max_n]
        importe = f"${float(item.get('importe') or 0):.2f}"
        draw_text(cant, margin, y, size=6)
        draw_text(nombre, col_desc_x, y, size=6, bold=True)
        c.setFont("Helvetica", 6 * scale)
        w = c.stringWidth(importe, "Helvetica", 6 * scale)
        c.drawString(ancho_pt - margin - w, y, importe)
        y -= 4 * mm
        if item.get("notas_especiales"):
            draw_text(f"* {item.get('notas_especiales')}", col_desc_x, y, size=5)
            y -= 3.5 * mm
        if int(item.get("cantidad") or 1) > 1:
            try:
                pu = f"${float(item.get('precio_unitario') or 0):.2f} c/u"
                draw_text(pu, col_desc_x, y, size=5)
                y -= 3.5 * mm
            except:
                pass
        y -= 1 * mm
        if y < 15 * mm:
            break

    y -= 1 * mm
    c.setDash(1, 2)
    c.setStrokeColor(HexColor(0x888888))
    c.line(margin, y, ancho_pt - margin, y)
    c.setDash()
    y -= 5 * mm

    for mp in (orden.get("metodos_pago") or []):
        nombre = str(mp.get("metodo_pago_nombre") or "PAGO").upper()
        monto = f"${float(mp.get('monto') or 0):.2f}"
        draw_text(f"PAGO {nombre}", margin, y, size=6)
        w = c.stringWidth(monto, "Helvetica", 6 * scale)
        c.drawString(ancho_pt - margin - w, y, monto)
        y -= 4 * mm

    y -= 1 * mm
    c.setLineWidth(0.6 * mm)
    draw_line(y)
    c.setLineWidth(0.25 * mm)
    y -= 6 * mm
    total = f"${float(orden.get('total_final') or 0):.2f}"
    draw_text(label_total, margin, y, size=8, bold=True)
    w = c.stringWidth(total, "Helvetica-Bold", 8 * scale)
    c.drawString(ancho_pt - margin - w, y, total)
    y -= 7 * mm
    c.setLineWidth(0.6 * mm)
    draw_line(y)
    c.setLineWidth(0.25 * mm)
    y -= 6 * mm

    draw_centered(foot_l1, y, size=6, bold=True)
    y -= 4 * mm
    draw_centered(foot_l2, y, size=6, bold=True)

    c.showPage()
    c.save()
    return buf.getvalue()


def generar_pdf_base64(lineas: list[str], ancho_mm: int = 58, **kw) -> str:
    pdf = generar_pdf_ticket(lineas, ancho_mm=ancho_mm, **kw)
    return base64.b64encode(pdf).decode("ascii")
