from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

@dataclass
class Extras:
    """
    Clase que representa un extra disponible para una reservación en el sistema de reservas.
    """
    id: UUID = field(default_factory=uuid4)
    sucursal_id: UUID
    nombre: str
    descripcion: str
    precio: float
    unidad: str
    activo: bool = True
    creado: datetime = field(default_factory=datetime.now)
    creado_por: str
    modificado: datetime = field(default_factory=datetime.now)
    modificado_por: str