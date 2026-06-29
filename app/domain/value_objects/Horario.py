from dataclasses import dataclass, field
from datetime import datetime, time

@dataclass(frozen=True)
class Horario:
    """
    Clase que representa un horario específico con hora de inicio y hora de fin.
    """
    hora_inicio: datetime
    hora_fin: datetime

    def __post_init__(self) -> None:
        if self.hora_inicio >= self.hora_fin:
            raise ValueError("La hora de inicio debe ser anterior a la hora de fin.")
    
    def duracion_minutos(self) -> int:
        """
        Calcula la duración del horario en minutos.
        """
        duracion = self.hora_fin - self.hora_inicio
        return int(duracion.total_seconds() / 60)    
    