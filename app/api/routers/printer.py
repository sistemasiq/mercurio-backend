"""
app/api/routers/printer.py
Módulo impresión universal: PrinterService + GdiAdapter reutilizable.
Endpoints: GET /printers, GET /printers/meta, config por sucursal, print/preview.
"""

from __future__ import annotations

import base64

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.api.deps import get_current_user, require_permission
from app.core.database import get_db
from app.repositories.printer_repository import (
    delete_config,
    get_config_por_sucursal,
    get_config_por_tipo,
    upsert_config,
    upsert_formato,
)
from app.schemas.auth import TokenData
from app.schemas.printer import (
    PrintTicketPayload,
    PrinterConfigPayload,
    PrinterConfigResponse,
    PrinterFormatoPayload,
    PrinterMeta,
)
from app.services.printer.detection import detectar_tipo, paper_size_para_tipo
from app.services.printer.service import get_printer_service

router = APIRouter(prefix="/api", tags=["Impresión"])

_SIN_SUCURSAL = HTTPException(
    status_code=status.HTTP_400_BAD_REQUEST,
    detail={"code": "SIN_SUCURSAL", "message": "El usuario no tiene sucursal asignada."},
)


def _branch_id(current_user: TokenData) -> str:
    if not current_user.branch_id:
        raise _SIN_SUCURSAL
    return str(current_user.branch_id)


@router.get("/printers", response_model=list[PrinterMeta], summary="Lista impresoras con metadata (GDI/WMI)")
async def listar_impresoras(
    current_user: TokenData = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db),
) -> list[PrinterMeta]:
    svc = get_printer_service()
    raws = await svc.list_printers()
    # Si PdfAdapter (Linux) retorna [], informar via header no-op pero devolver lista vacía para fallback frontend
    return [PrinterMeta(**r) for r in raws]


@router.get("/printers/meta", summary="Detección heurística para cada impresora")
async def printers_meta(
    current_user: TokenData = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db),
) -> dict:
    svc = get_printer_service()
    raws = await svc.list_printers()
    # Enriquecer con badge legible
    items = []
    for r in raws:
        tipo = r.get("tipo_detectado") or detectar_tipo(r.get("DriverName"), r.get("PaperNames"))
        items.append(
            {
                "Name": r.get("Name"),
                "DriverName": r.get("DriverName"),
                "PortName": r.get("PortName"),
                "PaperNames": r.get("PaperNames") or [],
                "tipo_detectado": tipo,
                "paper": paper_size_para_tipo(tipo),
                "badge": _badge(tipo),
            }
        )
    return {"printers": items, "count": len(items), "gdi_available": len(raws) > 0 or _is_windows()}


def _badge(tipo: str) -> str:
    mapping = {
        "ticket_58": "Detectado: Ticket 58mm",
        "ticket_80": "Detectado: Ticket 80mm",
        "etiqueta_60x40": "Detectado: Etiqueta 60x40",
        "a4": "Detectado: A4",
        "desconocida": "Detectado: Desconocida",
    }
    return mapping.get(tipo, "Detectado: Desconocida")


def _is_windows() -> bool:
    import platform

    return platform.system() == "Windows"


# ── Config por sucursal ───────────────────────────────────────────────────────

@router.get("/config-impresora", response_model=list[PrinterConfigResponse], summary="Lista config impresoras de la sucursal")
async def listar_config(
    current_user: TokenData = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db),
) -> list[PrinterConfigResponse]:
    rows = await get_config_por_sucursal(conn, _branch_id(current_user))
    return [
        PrinterConfigResponse(
            id=str(r["id"]),
            sucursal_id=str(r["sucursal_id"]),
            tipo=r["tipo"],
            nombre_impresora=r["nombre_impresora"],
            ancho_mm=r["ancho_mm"],
            alto_mm=r["alto_mm"],
            driver_detectado=r["driver_detectado"],
            tipo_detectado=r["tipo_detectado"],
            paper_names=r["paper_names"] or [],
            override_manual=r["override_manual"],
        )
        for r in rows
    ]


@router.put("/config-impresora", response_model=PrinterConfigResponse, summary="Guarda impresora por defecto (ticket o etiqueta)")
async def guardar_config(
    payload: PrinterConfigPayload,
    current_user: TokenData = Depends(require_permission("cajas:crear")),
    conn: asyncpg.Connection = Depends(get_db),
) -> PrinterConfigResponse:
    sucursal_id = _branch_id(current_user)
    # Validar ancho según tipo si no se manda
    ancho = payload.ancho_mm
    alto = payload.alto_mm
    if payload.tipo == "etiqueta":
        ancho = ancho or 60
        alto = alto or 40
    else:
        ancho = ancho or 58
        # 58mm=228 hundredths, 80mm=315 - parametrizado, no hardcodeado en servicio
        if ancho not in (58, 80):
            ancho = 58

    # Heurística si no viene tipo_detectado: usar ancho elegido
    tipo_detectado = payload.tipo_detectado
    if not tipo_detectado:
        if payload.tipo == "etiqueta":
            tipo_detectado = "etiqueta_60x40"
        elif ancho == 80:
            tipo_detectado = "ticket_80"
        elif ancho == 58:
            tipo_detectado = "ticket_58"
        else:
            tipo_detectado = "desconocida"

    row = await upsert_config(
        conn,
        sucursal_id=sucursal_id,
        tipo=payload.tipo,
        nombre_impresora=payload.nombre_impresora,
        ancho_mm=ancho,
        alto_mm=alto,
        tipo_detectado=tipo_detectado,
        override_manual=payload.override_manual,
        modificado_por=current_user.sub,
    )
    return PrinterConfigResponse(
        id=str(row["id"]),
        sucursal_id=str(row["sucursal_id"]),
        tipo=row["tipo"],
        nombre_impresora=row["nombre_impresora"],
        ancho_mm=row["ancho_mm"],
        alto_mm=row["alto_mm"],
        driver_detectado=row["driver_detectado"],
        tipo_detectado=row["tipo_detectado"],
        paper_names=row["paper_names"] or [],
        override_manual=row["override_manual"],
    )


@router.put("/config-formato", response_model=PrinterConfigResponse, summary="Guarda solo formato (ancho) desacoplado")
async def guardar_formato(
    payload: PrinterFormatoPayload,
    current_user: TokenData = Depends(require_permission("cajas:crear")),
    conn: asyncpg.Connection = Depends(get_db),
) -> PrinterConfigResponse:
    sucursal_id = _branch_id(current_user)
    if payload.tipo == "etiqueta":
        payload.ancho_mm = 60
        payload.alto_mm = 40
    elif payload.ancho_mm not in (58, 80, 60, 210):
        raise HTTPException(status_code=400, detail="ancho debe ser 58,80,60,210")
    row = await upsert_formato(conn, sucursal_id, payload.tipo, payload.ancho_mm, payload.alto_mm, modificado_por=current_user.sub)
    return PrinterConfigResponse(id=str(row["id"]), sucursal_id=str(row["sucursal_id"]), tipo=row["tipo"], nombre_impresora=row["nombre_impresora"], ancho_mm=row["ancho_mm"], alto_mm=row["alto_mm"], driver_detectado=row["driver_detectado"], tipo_detectado=row["tipo_detectado"], paper_names=row["paper_names"] or [], override_manual=row["override_manual"])

@router.delete("/config-impresora/{tipo}", status_code=status.HTTP_204_NO_CONTENT, summary="Elimina config de un tipo", response_model=None)
async def eliminar_config(
    tipo: str,
    current_user: TokenData = Depends(require_permission("cajas:crear")),
    conn: asyncpg.Connection = Depends(get_db),
) -> None:
    if tipo not in ("ticket", "etiqueta"):
        raise HTTPException(status_code=400, detail="Tipo debe ser ticket|etiqueta")
    await delete_config(conn, _branch_id(current_user), tipo)

# ── Print / Preview ─────────────────────────────────────────────────────────

def _resolver_ancho(payload: PrintTicketPayload, config_row: dict | None) -> int:
    if payload.ancho_mm:
        return payload.ancho_mm
    if config_row and config_row.get("ancho_mm"):
        return int(config_row["ancho_mm"])
    if payload.tipo == "etiqueta":
        return 60
    return 58


@router.post("/print/ticket/preview", summary="Genera PDF base64 para preview (no imprime)")
async def preview_ticket(
    payload: PrintTicketPayload,
    current_user: TokenData = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db),
) -> dict:
    svc = get_printer_service()
    sucursal_id = _branch_id(current_user) if current_user.branch_id else None
    config_row = None
    if sucursal_id and payload.tipo:
        try:
            config_row = await get_config_por_tipo(conn, sucursal_id, payload.tipo)
        except Exception:
            config_row = None
    ancho = _resolver_ancho(payload, config_row)
    data = _payload_a_data(payload)
    pdf_bytes = await svc.preview(data, ancho_mm=ancho)
    b64 = base64.b64encode(pdf_bytes).decode("ascii")
    return {"pdfBase64": b64, "ancho_mm": ancho}


@router.post("/print/ticket", summary="Impresión directa silenciosa al spooler (GDI) o fallback PDF")
async def print_ticket(
    payload: PrintTicketPayload,
    current_user: TokenData = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db),
) -> dict:
    svc = get_printer_service()
    sucursal_id = _branch_id(current_user) if current_user.branch_id else None

    # Resolver impresora: payload.printerName > config por tipo > primera detectada (ignora placeholder)
    printer_name = payload.printerName
    if printer_name == "__SIN_ASIGNAR__":
        printer_name = None
    config_row = None
    if sucursal_id and payload.tipo:
        try:
            config_row = await get_config_por_tipo(conn, sucursal_id, payload.tipo)
        except Exception:
            config_row = None
        if not printer_name and config_row:
            cand = config_row["nombre_impresora"]
            if cand and cand != "__SIN_ASIGNAR__":
                printer_name = cand

    if not printer_name:
        # Intentar primera impresora detectada
        try:
            printers = await svc.list_printers()
            if printers:
                printer_name = printers[0].get("Name")
        except Exception:
            pass

    # Si aún no hay impresora (Linux sin GDI), PdfAdapter hará fallback
    if not printer_name:
        printer_name = "PDF"

    ancho = _resolver_ancho(payload, config_row)
    data = _payload_a_data(payload)

    try:
        result = await svc.print(data, printer_name, ancho_mm=ancho)
        return result
    except Exception as exc:
        # Fallback a PDF si GDI falla (impresora no válida, sin Windows, etc.)
        from app.services.printer.pdf_ticket import generar_pdf_base64

        lineas = data.get("lineas") or data.get("raw_lines") or ["Error GDI, fallback PDF", str(exc)[:60]]
        b64 = generar_pdf_base64(lineas, ancho_mm=ancho)
        return {"pdfBase64": b64, "printer": printer_name, "ancho_mm": ancho, "fallback": True, "error": str(exc)[:200]}


def _payload_a_data(payload: PrintTicketPayload) -> dict:
    if payload.data is not None:
        # si viene { lineas, texto } dentro de data
        return payload.data
    d: dict = {}
    if payload.lineas is not None:
        d["lineas"] = payload.lineas
    if payload.texto is not None:
        d["texto"] = payload.texto
    # Demo por defecto si vacío
    if not d:
        tipo = payload.tipo or "ticket"
        if tipo == "etiqueta":
            d["lineas"] = ["WOOW KIDS - ETIQUETA", "60x40mm", "Prueba OK", "----------------"]
        else:
            d["lineas"] = [
                "WOOW KIDS - Ticket Prueba",
                "Sucursal: Demo",
                "Fecha: 2026-09-15",
                "------------------------------",
                "1 x Entrada Niño    $150.00",
                "------------------------------",
                "TOTAL              $150.00",
                "",
                "¡Gracias por su visita!",
            ]
    return d


@router.get("/print/ticket/pdf/{b64_preview}", summary="Descarga PDF desde preview (compat)")
async def download_pdf(b64_preview: str) -> Response:
    try:
        pdf_bytes = base64.b64decode(b64_preview)
    except Exception:
        raise HTTPException(status_code=400, detail="Base64 inválido")
    return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": "inline; filename=ticket.pdf"})
