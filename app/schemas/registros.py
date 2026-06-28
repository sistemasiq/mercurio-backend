from pydantic import BaseModel,Field
from typing import Optional,List
from app.schemas.ninos import NinoIn
from app.schemas.tutores import TutorIn
from app.schemas.pagos import PagoIn
from uuid import UUID

class DetalleIn(BaseModel):
   nino: NinoIn
   productoId: UUID
   cantidad: int = Field(gt=0)
   pulseraId: UUID

class OnboardingRequest(BaseModel):
   sucursalId: UUID
   tutor: TutorIn
   parentesco: str
   detalles: List[DetalleIn]
   pagos: List[PagoIn]


class OnboardingResponse(BaseModel):
   registroId: UUID
   total: float
   pagado: float
   estado: str

class CheckoutResponse(BaseModel):
   detalleId: str
   registroId: str
   horasExtra: int
   totalExtra: float
   ninosRestantes: int

class ProductoResponse(BaseModel):
   id: UUID
   nombre: str
   precio_unitario: float
   descripcion: Optional[str]


class DetalleActivoResponse(BaseModel):
   registro_id: UUID
   detalle_id: UUID
   nino: str
   notas: Optional[str]
   edad: int
   tutor: str
   telefono: str
   parentesco: str
   pulsera: str
   minutos_pagados: float
   minutos_transcurridos: float
