"""
app/utils/csv_export.py
Utilidad compartida para exportar listados a CSV (B7: reportes y
exportación). No usa pandas ni librerías externas: solo el módulo `csv`
de la librería estándar sobre un buffer en memoria, entregado como
`StreamingResponse`.
"""

from __future__ import annotations

import csv
import io
from collections.abc import Iterable, Sequence
from typing import Any

from fastapi.responses import StreamingResponse


def csv_streaming_response(
    fieldnames: Sequence[str],
    rows: Iterable[dict[str, Any]],
    filename: str,
) -> StreamingResponse:
    """Genera un CSV a partir de una lista de dicts y lo entrega como
    descarga. `extrasaction="ignore"` permite pasar dicts con más campos
    que las columnas pedidas (p. ej. el `model_dump()` de un esquema)."""
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(fieldnames), extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
