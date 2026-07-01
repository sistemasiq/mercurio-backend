from dataclasses import dataclass, field
from datetime import datetime
from email.policy import default
from uuid import UUID, uuid4

@dataclass
class Metodos_Pago:
    """
    Clase que representa un método de pago disponible en el sistema de reservas.
    """
    id: UUID = field(default_factory=uuid4)
    nombre: str
    descripcion: str
    activo: bool = True
    creado: datetime = field(default_factory=datetime.now)
    creado_por: str
    modificado: datetime = field(default_factory=datetime.now)
    modificado_por: str

    def __post_init__(self):
        if not self.nombre:
            raise ValueError("El nombre del método de pago no puede estar vacío.")
        if not self.descripcion:
            raise ValueError("La descripción del método de pago no puede estar vacía.")
        if not self.creado_por:
            raise ValueError("El campo 'creado_por' no puede estar vacío.")
        if not self.modificado_por:
            raise ValueError("El campo 'modificado_por' no puede estar vacío.")
        