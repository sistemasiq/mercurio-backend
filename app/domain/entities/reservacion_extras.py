from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

@dataclass
class ReservacionExtras:
    """
    Clase que representa los extras asociados a una reservación en el sistema de reservas.
    """
    id: UUID = field(default_factory=uuid4)
    reservacion_id: UUID
    extra_id: UUID
    cantidad: int
    precio_unitario: float
    subtotal: float = field(init=False)
    creado: datetime = field(default_factory=datetime.now)
    creado_por: str

    def __post_init__(self):
        self.subtotal = self.cantidad * self.precio_unitario