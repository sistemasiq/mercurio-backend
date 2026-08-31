from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

CELULAR_PATTERN = r"^\d{10}$"


class ConfiguracionLealtadBase(BaseModel):
    porcentaje_retorno: float = Field(0, ge=0, le=100)
    dias_caducidad: int = Field(..., gt=0)
    valor_punto: float = Field(1.00, gt=0)
    activo: bool = True
    otorga_puntos_comandas: bool = True
    otorga_puntos_reservaciones: bool = True
    otorga_puntos_checkin: bool = True


class ConfiguracionLealtadOut(ConfiguracionLealtadBase):
    sucursal_id: UUID
    creado: datetime
    creado_por: UUID | None
    modificado: datetime | None
    modificado_por: UUID | None

    model_config = {"from_attributes": True}


class SaldoPuntosOut(BaseModel):
    sucursal_id: UUID
    celular: str
    saldo: int


class ReporteLealtadOut(BaseModel):
    sucursal_id: UUID
    total_otorgado: int
    total_redimido: int
    total_caducado: int
    saldo_vigente: int
    clientes_con_saldo: int


class MovimientoPuntoOut(BaseModel):
    id: UUID
    sucursal_id: UUID
    celular: str
    lote_id: UUID | None
    comanda_id: UUID | None
    tipo: str
    puntos: int
    saldo_resultante: int
    notas: str | None
    creado: datetime
    creado_por: UUID | None

    model_config = {"from_attributes": True}
