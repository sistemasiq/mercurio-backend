from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4
from domain.entities.reservaciones import Reservacion
from domain.entities.metodos_pago import Metodos_Pago

@dataclass
class Pagos_Reservacion:
    """
    Clase que representa un pago asociado a una reservación en el sistema de reservas.
    """
    id: UUID = field (default_factory=uuid4)
    reservacion_id: UUID
    metodo_pago_id: UUID
    monto: float
    fecha_pago: datetime = field(default_factory=datetime.now)
    notas: str
    creado_por: str
    creado: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if self.monto <= 0:
            raise ValueError("El monto del pago debe ser mayor a cero.")
        if not self.notas:
            raise ValueError("Las notas del pago no pueden estar vacías.")
        if not self.creado_por:
            raise ValueError("El campo 'creado_por' no puede estar vacío.")
        