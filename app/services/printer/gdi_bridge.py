"""
Bridge GDI via PowerShell + System.Drawing.Printing + win32print (fix enumeración).
Solo fix de detección (per-usuario vs SYSTEM) — mantiene el diseño original del ticket.
"""

from __future__ import annotations

import asyncio
import json
import platform
import subprocess
import textwrap
from typing import Any
import logging

log = logging.getLogger(__name__)

def _is_windows() -> bool:
    return platform.system() == "Windows"

_PS_CANDIDATES = [
    r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe",
    r"C:\Windows\SysWOW64\WindowsPowerShell\v1.0\powershell.exe",
    "powershell.exe",
    "powershell",
]

def _list_via_win32print() -> list[dict[str, Any]]:
    try:
        import win32print
        result: dict[str, dict[str, Any]] = {}
        for flags in (6, 2, 6 | 32):
            try:
                for p in win32print.EnumPrinters(flags, None, 2) or []:
                    if isinstance(p, dict):
                        name = (p.get("pPrinterName") or "").strip()
                        if name and name not in result:
                            result[name] = {"Name": name, "DriverName": p.get("pDriverName") or "", "PortName": p.get("pPortName") or "", "PaperNames": []}
            except Exception as e:
                log.debug("win32print %s: %s", flags, e)
        return list(result.values())
    except ImportError:
        return []
    except Exception as e:
        log.debug("win32print error: %s", e)
        return []

async def listar_impresoras_windows() -> list[dict[str, Any]]:
    if not _is_windows():
        return []

    merged: dict[str, dict[str, Any]] = {}
    for item in _list_via_win32print():
        if item["Name"] not in merged:
            merged[item["Name"]] = item

    # PowerShell simple (el que te lista 4 con Get-CimInstance)
    ps_simple = textwrap.dedent(r"""
        $ErrorActionPreference='SilentlyContinue'
        $list = Get-CimInstance Win32_Printer -ErrorAction SilentlyContinue | Select-Object Name,DriverName,PortName
        if(-not $list){ $list = Get-WmiObject Win32_Printer -ErrorAction SilentlyContinue | Select-Object Name,DriverName,PortName }
        $out=@(); Add-Type -AssemblyName System.Drawing -ErrorAction SilentlyContinue | Out-Null
        foreach($p in $list){
            $papers=@(); try{ $ps=New-Object System.Drawing.Printing.PrinterSettings -ErrorAction SilentlyContinue; $ps.PrinterName=$p.Name; foreach($sz in $ps.PaperSizes){ $papers+=$sz.PaperName } }catch{}
            $out+=[PSCustomObject]@{ Name=$p.Name; DriverName=$p.DriverName; PortName=$p.PortName; PaperNames=$papers }
        }
        $out | ConvertTo-Json -Depth 3 -Compress
    """)
    # Probar cada exe hasta que uno devuelva JSON
    text = None
    for exe in _PS_CANDIDATES:
        try:
            proc = await asyncio.create_subprocess_exec(exe, "-NoProfile","-ExecutionPolicy","Bypass","-Command", ps_simple, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=8)
            if proc.returncode==0 and stdout:
                text = stdout.decode("utf-8", errors="ignore").strip()
                if text and text != "null":
                    break
        except:
            continue
    if text and text not in ("", "null", "[]"):
        try:
            data = json.loads(text)
            if isinstance(data, dict): data=[data]
            for item in data or []:
                name=(item.get("Name") or "").strip()
                if name and name not in merged:
                    merged[name]={"Name": name, "DriverName": item.get("DriverName") or "", "PortName": item.get("PortName") or "", "PaperNames": item.get("PaperNames") or []}
        except:
            pass

    if not merged:
        log.warning("No se detectaron impresoras GDI. Fallback PDF disponible.")

    result=[]
    for v in merged.values():
        result.append({"Name": v["Name"], "DriverName": v["DriverName"], "PortName": v["PortName"], "PaperNames": v["PaperNames"] or []})
    result.sort(key=lambda x: x["Name"].lower())
    return result


async def imprimir_pdf_gdi(printer_name: str, pdf_bytes: bytes) -> None:
    if not _is_windows():
        raise RuntimeError("GDI solo disponible en Windows")
    if not printer_name:
        raise ValueError("nombre_impresora requerido")
    import tempfile, os
    tmp_pdf = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tf:
            tf.write(pdf_bytes)
            tmp_pdf = tf.name
        ps = textwrap.dedent(
            f"""
            $ErrorActionPreference='Stop'
            $pdfPath = '{tmp_pdf.replace("'", "''").replace(chr(92), chr(92)+chr(92))}'
            $printerName = '{printer_name.replace("'", "''")}'
            try {{
                Start-Process -FilePath $pdfPath -Verb PrintTo -ArgumentList $printerName -WindowStyle Hidden
                Start-Sleep -Seconds 2
                exit 0
            }} catch {{}}
            throw "PDF PrintTo falló: $($_.Exception.Message)"
            """
        )
        last_err = None
        for exe in _PS_CANDIDATES:
            tmp_ps = None
            try:
                with tempfile.NamedTemporaryFile(mode="w", suffix=".ps1", delete=False, encoding="utf-8") as tf:
                    tf.write(ps)
                    tmp_ps = tf.name
                import subprocess

                def _run():
                    r = subprocess.run([exe, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", tmp_ps], capture_output=True, timeout=15)
                    return r.returncode, r.stdout.decode("utf-8", errors="ignore"), r.stderr.decode("utf-8", errors="ignore")

                rc, out, err = await asyncio.to_thread(_run)
                if rc == 0:
                    log.info("imprimir_pdf_gdi ok -> %s", printer_name)
                    return
                last_err = err[:600] or out[:400] or f"rc {rc}"
            except Exception as e:
                last_err = str(e)[:400]
            finally:
                if tmp_ps:
                    try:
                        os.unlink(tmp_ps)
                    except:
                        pass
        try:
            import win32print

            hprinter = win32print.OpenPrinter(printer_name)
            try:
                win32print.StartDocPrinter(hprinter, 1, ("Ticket WYSIWYG", None, "RAW"))
                win32print.StartPagePrinter(hprinter)
                win32print.WritePrinter(hprinter, pdf_bytes)
                win32print.EndPagePrinter(hprinter)
                win32print.EndDocPrinter(hprinter)
                log.info("imprimir_pdf_gdi win32print RAW PDF ok -> %s", printer_name)
                return
            finally:
                win32print.ClosePrinter(hprinter)
        except Exception as e:
            last_err = f"{last_err or ''} | win32print:{str(e)[:300]}"
        raise RuntimeError(f"Error PDF GDI: {last_err or 'PrintTo falló'}")
    finally:
        if tmp_pdf:
            try:
                import time

                await asyncio.to_thread(lambda: (time.sleep(3), os.unlink(tmp_pdf)))
            except:
                pass


async def imprimir_gdi_wysiwyg(
    printer_name: str,
    orden: dict,
    ancho_mm: int = 80,
) -> None:
    """WYSIWYG 80mm con negritas reales vía System.Drawing — 1 botón silencioso sin PDF."""
    if not _is_windows():
        raise RuntimeError("GDI solo disponible en Windows")
    if not printer_name:
        raise ValueError("nombre_impresora requerido")
    import base64

    payload = base64.b64encode(json.dumps(orden, ensure_ascii=False).encode("utf-8")).decode()
    ps = textwrap.dedent(
        f"""
        Add-Type -AssemblyName System.Drawing
        $b64 = '{payload}'
        $json = [System.Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($b64))
        $orden = $json | ConvertFrom-Json
        $printerName = '{printer_name.replace("'", "''")}'
        $anchoMm = {ancho_mm}
        $pd = New-Object System.Drawing.Printing.PrintDocument
        $pd.PrinterSettings.PrinterName = $printerName
        if (-not $pd.PrinterSettings.IsValid) {{ throw "Impresora no válida: $printerName" }}
        $widthHundredths = [int](($anchoMm / 25.4) * 100)
        $pd.DefaultPageSettings.PaperSize = New-Object System.Drawing.Printing.PaperSize("WYSIWYG", $widthHundredths, 1200)
        $pd.DefaultPageSettings.Margins = New-Object System.Drawing.Printing.Margins(4,4,4,4)
        $pd.add_PrintPage({{
            param($sender,$e)
            $g = $e.Graphics
            $fTitle = New-Object System.Drawing.Font("Arial", 11, [System.Drawing.FontStyle]::Bold)
            $fAddr = New-Object System.Drawing.Font("Arial", 6)
            $fBold6 = New-Object System.Drawing.Font("Arial", 6, [System.Drawing.FontStyle]::Bold)
            $fReg6 = New-Object System.Drawing.Font("Arial", 6)
            $fBold8 = New-Object System.Drawing.Font("Arial", 8, [System.Drawing.FontStyle]::Bold)
            $brush = [System.Drawing.Brushes]::Black
            $penDash = New-Object System.Drawing.Pen([System.Drawing.Color]::Black, 0.5)
            $penDash.DashStyle = [System.Drawing.Drawing2D.DashStyle]::Dash
            $penSolid = New-Object System.Drawing.Pen([System.Drawing.Color]::Black, 0.5)
            $penThick = New-Object System.Drawing.Pen([System.Drawing.Color]::Black, 1.2)
            $x = 8; $y = 8; $w = $e.PageBounds.Width - 16
            # WOOW KIDS
            $sz = $g.MeasureString("WOOW KIDS", $fTitle)
            $g.DrawString("WOOW KIDS", $fTitle, $brush, ($w - $sz.Width)/2 + $x, $y); $y += 14
            $sz = $g.MeasureString("Nigromante 391, Peña", $fAddr)
            $g.DrawString("Nigromante 391, Peña", $fAddr, $brush, ($w - $sz.Width)/2 + $x, $y); $y += 9
            $sz = $g.MeasureString("59375 La Piedad de Cabadas, Mich.", $fAddr)
            $g.DrawString("59375 La Piedad de Cabadas, Mich.", $fAddr, $brush, ($w - $sz.Width)/2 + $x, $y); $y += 10
            $g.DrawLine($penDash, $x, $y, $x + $w, $y); $y += 8
            # TICKET / FECHA
            try {{ $fecha = (Get-Date $orden.fecha_hora -Format "dd MMM yyyy"); $hora = (Get-Date $orden.fecha_hora -Format "hh:mm tt") }} catch {{ $fecha = ""; $hora = "" }}
            $g.DrawString("TICKET: $($orden.titulo)", $fBold6, $brush, $x, $y)
            $sz = $g.MeasureString("FECHA: $fecha", $fBold6); $g.DrawString("FECHA: $fecha", $fBold6, $brush, $x + $w - $sz.Width, $y); $y += 9
            $g.DrawString("CAJERO: $(([string]$orden.creado_por_nombre).Split(' ')[0])", $fBold6, $brush, $x, $y)
            $sz = $g.MeasureString("HORA: $hora", $fBold6); $g.DrawString("HORA: $hora", $fBold6, $brush, $x + $w - $sz.Width, $y); $y += 10
            $g.DrawLine($penDash, $x, $y, $x + $w, $y); $y += 8
            # CANT / DESCRIPCIÓN / IMP
            $g.DrawString("CANT", $fBold6, $brush, $x, $y)
            $sz = $g.MeasureString("IMP", $fBold6); $g.DrawString("IMP", $fBold6, $brush, $x + $w - $sz.Width, $y)
            $g.DrawString("DESCRIPCIÓN", $fBold6, $brush, $x + 28, $y); $y += 8
            $g.DrawLine($penSolid, $x, $y, $x + $w, $y); $y += 8
            foreach ($it in $orden.detalles) {{
                if ($it.nombre_combo_padre) {{
                    $g.DrawString("  - $($it.cantidad)x $($it.producto_nombre)", $fReg6, $brush, $x + 14, $y); $y += 8
                    continue
                }}
                $g.DrawString("$($it.cantidad)", $fReg6, $brush, $x, $y)
                $g.DrawString("$($it.producto_nombre)", $fBold6, $brush, $x + 18, $y)
                $imp = "{{0:F2}}" -f [double]$it.importe; $imp = "`$$imp"
                $sz = $g.MeasureString($imp, $fReg6); $g.DrawString($imp, $fReg6, $brush, $x + $w - $sz.Width, $y); $y += 8
                if ($it.notas_especiales) {{ $g.DrawString("* $($it.notas_especiales)", $fReg6, $brush, $x + 18, $y); $y += 7 }}
            }}
            $g.DrawLine($penDash, $x, $y, $x + $w, $y); $y += 8
            foreach ($mp in $orden.metodos_pago) {{
                $imp = "{{0:F2}}" -f [double]$mp.monto; $imp = "`$$imp"
                $g.DrawString("PAGO $($mp.metodo_pago_nombre.ToUpper())", $fReg6, $brush, $x, $y)
                $sz = $g.MeasureString($imp, $fReg6); $g.DrawString($imp, $fReg6, $brush, $x + $w - $sz.Width, $y); $y += 8
            }}
            $g.DrawLine($penThick, $x, $y, $x + $w, $y); $y += 8
            $total = "{{0:F2}}" -f [double]$orden.total_final; $total = "`$$total"
            $g.DrawString("TOTAL VENTA", $fBold8, $brush, $x, $y)
            $sz = $g.MeasureString($total, $fBold8); $g.DrawString($total, $fBold8, $brush, $x + $w - $sz.Width, $y); $y += 10
            $g.DrawLine($penThick, $x, $y, $x + $w, $y); $y += 10
            $sz = $g.MeasureString("*** GRACIAS POR SU COMPRA ***", $fBold6); $g.DrawString("*** GRACIAS POR SU COMPRA ***", $fBold6, $brush, ($w - $sz.Width)/2 + $x, $y); $y += 9
            $sz = $g.MeasureString("ESTE NO ES UN COMPROBANTE FISCAL", $fBold6); $g.DrawString("ESTE NO ES UN COMPROBANTE FISCAL", $fBold6, $brush, ($w - $sz.Width)/2 + $x, $y)
            $e.HasMorePages = $false
        }})
        $pd.Print()
        """
    )
    import tempfile, os, subprocess

    tmp = None
    last_err = None
    for exe in _PS_CANDIDATES:
        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".ps1", delete=False, encoding="utf-8") as tf:
                tf.write(ps); tmp = tf.name
            def _run():
                r = subprocess.run([exe, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", tmp], capture_output=True, timeout=20)
                return r.returncode, r.stdout.decode("utf-8", errors="ignore"), r.stderr.decode("utf-8", errors="ignore")
            rc, out, err = await asyncio.to_thread(_run)
            if rc == 0:
                log.info("imprimir_gdi_wysiwyg ok -> %s", printer_name)
                return
            last_err = err.strip() or out.strip() or f"rc {rc}"
            log.warning("imprimir_gdi_wysiwyg %s failed rc=%s err=%s", exe, rc, last_err[:700])
        except Exception as e:
            last_err = f"{type(e).__name__}: {str(e)[:400]}"
        finally:
            if tmp:
                try: os.unlink(tmp)
                except: pass
    raise RuntimeError(f"Error GDI WYSIWYG: {last_err or 'PrintDocument falló'}")


async def imprimir_gdi(
    printer_name: str,
    lineas: list[str],
    ancho_mm: int = 58,
    font_name: str = "Consolas",
    font_size: float = 8.0,
    bold_lines: set[int] | None = None,
) -> None:
    if not _is_windows():
        raise RuntimeError("GDI solo disponible en Windows")
    if not printer_name:
        raise ValueError("nombre_impresora requerido")
    import base64
    payload = base64.b64encode(json.dumps(lineas, ensure_ascii=False).encode("utf-8")).decode()
    bold_payload = base64.b64encode(json.dumps(sorted(list(bold_lines or [])), ensure_ascii=False).encode("utf-8")).decode()
    ps = textwrap.dedent(
        f"""
        Add-Type -AssemblyName System.Drawing
        $b64 = '{payload}'
        $json = [System.Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($b64))
        $lineas = $json | ConvertFrom-Json
        $b64Bold = '{bold_payload}'
        $jsonBold = [System.Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($b64Bold))
        $boldIdx = @($jsonBold | ConvertFrom-Json)
        $printerName = '{printer_name.replace("'", "''")}'
        $anchoMm = {ancho_mm}
        $fontName = '{font_name}'
        $fontSize = {str(font_size).replace(",", ".")}
        $pd = New-Object System.Drawing.Printing.PrintDocument
        $pd.PrinterSettings.PrinterName = $printerName
        if (-not $pd.PrinterSettings.IsValid) {{ throw "Impresora no válida: $printerName" }}
        $widthHundredths = [int](($anchoMm / 25.4) * 100)
        $pd.DefaultPageSettings.PaperSize = New-Object System.Drawing.Printing.PaperSize("Custom", $widthHundredths, 1200)
        $pd.DefaultPageSettings.Margins = New-Object System.Drawing.Printing.Margins(5,5,5,5)
        $pd.add_PrintPage({{
            param($sender,$e)
            $fontReg = New-Object System.Drawing.Font($fontName, $fontSize)
            $fontBold = New-Object System.Drawing.Font($fontName, $fontSize, [System.Drawing.FontStyle]::Bold)
            $brush = [System.Drawing.Brushes]::Black
            $x = 5; $y = 5; $lineH = $fontReg.GetHeight($e.Graphics) + 1
            for ($i=0; $i -lt $lineas.Count; $i++) {{
                $ln = $lineas[$i]
                $f = if ($boldIdx -contains $i) {{ $fontBold }} else {{ $fontReg }}
                $e.Graphics.DrawString($ln, $f, $brush, $x, $y)
                $y += $lineH
            }}
            $e.HasMorePages = $false
        }})
        $pd.Print()
        """
    )
    # Usar subprocess.run vía to_thread para evitar NotImplementedError de Proactor
    import tempfile, os
    tmp=None
    last_err=None
    for exe in _PS_CANDIDATES:
        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".ps1", delete=False, encoding="utf-8") as tf:
                tf.write(ps); tmp=tf.name
            def _run():
                r=subprocess.run([exe,"-NoProfile","-ExecutionPolicy","Bypass","-File",tmp], capture_output=True, timeout=20)
                return r.returncode, r.stdout.decode("utf-8", errors="ignore"), r.stderr.decode("utf-8", errors="ignore")
            rc,out,err = await asyncio.to_thread(_run)
            if rc==0:
                return
            last_err=err.strip() or out.strip() or f"rc {rc}"
        except Exception as e:
            last_err=f"{type(e).__name__}: {str(e)[:300]}"
        finally:
            if tmp:
                try: os.unlink(tmp)
                except: pass
    raise RuntimeError(f"Error GDI: {last_err or 'PrintDocument falló'}")
