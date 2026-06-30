from dataclasses import dataclass
from datetime import time


@dataclass(frozen=True)
class Horario:
    """Rango horario de un evento (hora de inicio y fin dentro del mismo día)."""

    inicio: time
    fin: time

    def __post_init__(self) -> None:
        if self.inicio >= self.fin:
            raise ValueError("La hora de inicio debe ser anterior a la hora de fin.")

    def duracion_minutos(self) -> int:
        inicio_min = self.inicio.hour * 60 + self.inicio.minute
        fin_min = self.fin.hour * 60 + self.fin.minute
        return fin_min - inicio_min
