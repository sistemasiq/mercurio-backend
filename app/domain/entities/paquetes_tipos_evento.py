from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4
from domain.entities.reservaciones import Reservacion
from domain.entities.tipos_evento import Tipos_Evento

@dataclass
class Paquetes_Tipos_Evento:
    """
    Clase que representa la relación entre paquetes y tipos de evento en el sistema de reservas.
    """
    paquete_id: UUID
    tipo_evento_id: UUID

    def __post_init__(self):
        if not isinstance(self.paquete_id, UUID):
            raise ValueError("El campo 'paquete_id' debe ser un UUID válido.")
        if not isinstance(self.tipo_evento_id, UUID):
            raise ValueError("El campo 'tipo_evento_id' debe ser un UUID válido.")
        