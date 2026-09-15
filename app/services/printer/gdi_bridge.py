"""
Bridge GDI via PowerShell + System.Drawing.Printing.

Solo funciona en Windows con driver instalado. En Linux/Docker devuelve no-op.
"""

from __future__ import annotations

import asyncio
import json
import platform
import subprocess
import textwrap
from typing import Any


def _is_windows() -> bool:
    return platform.system() == "Windows"


async def listar_impresoras_windows() -> list[dict[str, Any]]:
    """Lista impresoras con metadata (Name, DriverName, PortName, PaperNames).

    Combina Win32_Printer (WMI) + PrinterSettings.InstalledPrinters + PaperSizes.
    Si no es Windows o falla, retorna [].
    """
    if not _is_windows():
        return []

    ps_script = textwrap.dedent(
        r"""
        $ErrorActionPreference = 'SilentlyContinue'
        Add-Type -AssemblyName System.Drawing | Out-Null
        $installed = [System.Drawing.Printing.PrinterSettings]::InstalledPrinters
        $wmi = Get-CimInstance Win32_Printer -ErrorAction SilentlyContinue
        $out = @()
        foreach ($name in $installed) {
            $wm = $wmi | Where-Object { $_.Name -eq $name } | Select-Object -First 1
            $driver = if ($wm) { $wm.DriverName } else { "" }
            $port = if ($wm) { $wm.PortName } else { "" }
            # PaperNames via PrinterSettings
            $papers = @()
            try {
                $ps = New-Object System.Drawing.Printing.PrinterSettings
                $ps.PrinterName = $name
                foreach ($sz in $ps.PaperSizes) { $papers += $sz.PaperName }
            } catch {}
            $out += [PSCustomObject]@{
                Name = $name
                DriverName = $driver
                PortName = $port
                PaperNames = $papers
            }
        }
        # Incluir también WMI que no estén en InstalledPrinters (virtuales)
        foreach ($wm in $wmi) {
            if ($installed -notcontains $wm.Name) {
                $out += [PSCustomObject]@{
                    Name = $wm.Name
                    DriverName = $wm.DriverName
                    PortName = $wm.PortName
                    PaperNames = @()
                }
            }
        }
        $out | ConvertTo-Json -Depth 3 -Compress
        """
    )

    try:
        proc = await asyncio.create_subprocess_exec(
            "powershell",
            "-NoProfile",
            "-Command",
            ps_script,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=8)
        if proc.returncode != 0 or not stdout:
            return []
        text = stdout.decode("utf-8", errors="ignore").strip()
        if not text:
            return []
        data = json.loads(text)
        if isinstance(data, dict):
            data = [data]
        # normalizar
        result = []
        for item in data or []:
            result.append(
                {
                    "Name": item.get("Name", ""),
                    "DriverName": item.get("DriverName", ""),
                    "PortName": item.get("PortName", ""),
                    "PaperNames": item.get("PaperNames") or [],
                }
            )
        return result
    except Exception:
        return []


async def imprimir_gdi(
    printer_name: str,
    lineas: list[str],
    ancho_mm: int = 58,
    font_name: str = "Consolas",
    font_size: float = 8.0,
) -> None:
    """Envía texto monoespaciado al spooler GDI de forma silenciosa."""
    if not _is_windows():
        raise RuntimeError("GDI solo disponible en Windows")
    if not printer_name:
        raise ValueError("nombre_impresora requerido")

    # Escapar para PowerShell single-quoted string
    # Pasamos líneas como JSON base64 para evitar inyección
    import base64

    payload = base64.b64encode(json.dumps(lineas, ensure_ascii=False).encode("utf-8")).decode()
    ps = textwrap.dedent(
        f"""
        Add-Type -AssemblyName System.Drawing
        $b64 = '{payload}'
        $json = [System.Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($b64))
        $lineas = $json | ConvertFrom-Json
        $printerName = '{printer_name.replace("'", "''")}'
        $anchoMm = {ancho_mm}
        $fontName = '{font_name}'
        $fontSize = {str(font_size).replace(",", ".")}
        $pd = New-Object System.Drawing.Printing.PrintDocument
        $pd.PrinterSettings.PrinterName = $printerName
        if (-not $pd.PrinterSettings.IsValid) {{ throw "Impresora no válida: $printerName" }}
        # PaperSize en hundredths of inch: 58mm=228, 80mm=315, 60mm=236
        $widthHundredths = [int](($anchoMm / 25.4) * 100)
        $pd.DefaultPageSettings.PaperSize = New-Object System.Drawing.Printing.PaperSize("Custom", $widthHundredths, 1200)
        $pd.DefaultPageSettings.Margins = New-Object System.Drawing.Printing.Margins(5,5,5,5)
        $yRef = @{{ Value = 0 }}
        $pd.add_PrintPage({{
            param($sender,$e)
            $font = New-Object System.Drawing.Font($fontName, $fontSize)
            $brush = [System.Drawing.Brushes]::Black
            $x = 5; $y = 5; $lineH = $font.GetHeight($e.Graphics) + 1
            foreach ($ln in $lineas) {{
                $e.Graphics.DrawString($ln, $font, $brush, $x, $y)
                $y += $lineH
            }}
            $e.HasMorePages = $false
        }})
        $pd.Print()
        """
    )
    proc = await asyncio.create_subprocess_exec(
        "powershell",
        "-NoProfile",
        "-Command",
        ps,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=15)
    if proc.returncode != 0:
        err = stderr.decode("utf-8", errors="ignore") if stderr else ""
        raise RuntimeError(f"Error GDI: {err.strip() or 'PrintDocument falló'}")
