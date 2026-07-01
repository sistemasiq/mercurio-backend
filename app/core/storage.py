from pathlib import Path

UPLOADS_DIR = Path("uploads")

IDENTIFICACIONES_DIR = UPLOADS_DIR / "identificaciones"
LLEGADAS_DIR = UPLOADS_DIR / "llegadas"

IDENTIFICACIONES_DIR.mkdir(parents=True, exist_ok=True)
LLEGADAS_DIR.mkdir(parents=True, exist_ok=True)
