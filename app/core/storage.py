import logging
from pathlib import Path

logger = logging.getLogger(__name__)

UPLOADS_DIR = Path("uploads")

IDENTIFICACIONES_DIR = UPLOADS_DIR / "identificaciones"
LLEGADAS_DIR = UPLOADS_DIR / "llegadas"
PRODUCTOS_DIR = UPLOADS_DIR / "productos"


def _crear_directorio(directorio: Path) -> None:
    """Crea el directorio si no existe. No debe tumbar el arranque de la app
    si el proceso no tiene permisos sobre uploads/ (p. ej. creada antes por
    otro usuario/Docker corriendo como root)."""
    try:
        directorio.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        logger.warning(
            "No se pudo crear %s por falta de permisos; las subidas a esta carpeta "
            "fallaran hasta que se cree manualmente.",
            directorio,
        )


_crear_directorio(IDENTIFICACIONES_DIR)
_crear_directorio(LLEGADAS_DIR)
_crear_directorio(PRODUCTOS_DIR)
