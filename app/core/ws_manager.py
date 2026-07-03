"""
app/core/ws_manager.py
Registro en memoria de conexiones WebSocket activas, agrupadas por sucursal.

Mismo patrón que el caché de permisos (app/services/permission_service.py):
estado global por proceso, sin backplane compartido. Solo funciona con un único
proceso worker — si el despliegue pasa a múltiples workers, esto necesitaría un
pub/sub externo (Redis) para que el broadcast llegue a todas las conexiones sin
importar en qué proceso quedaron.

Los AdministradorSistema (ven todas las sucursales) se agrupan bajo el canal "*".
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger("mercury.ws")

CANAL_GLOBAL = "*"


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: dict[str, set[WebSocket]] = {}

    async def connect(self, canal: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.setdefault(canal, set()).add(websocket)

    def disconnect(self, canal: str, websocket: WebSocket) -> None:
        conexiones = self._connections.get(canal)
        if conexiones is None:
            return
        conexiones.discard(websocket)
        if not conexiones:
            del self._connections[canal]

    async def broadcast(self, sucursal_id: str, message: dict[str, Any]) -> None:
        """Envía a las conexiones de esa sucursal y a las del canal global
        (AdministradorSistema, que ve todas las sucursales)."""
        for canal in {sucursal_id, CANAL_GLOBAL}:
            for websocket in list(self._connections.get(canal, ())):
                try:
                    await websocket.send_json(message)
                except Exception:
                    logger.debug("Conexion WS caida al hacer broadcast, se descarta", exc_info=True)
                    self.disconnect(canal, websocket)


manager = ConnectionManager()
