from uuid import UUID

from pydantic import BaseModel


class PaqueteTiposEventoBase(BaseModel):
    paquete_id: UUID
    tipo_evento_id: UUID


class PaqueteTiposEventoCreate(PaqueteTiposEventoBase): pass


class PaqueteTiposEventoOut(PaqueteTiposEventoBase):
    model_config = {'from_attributes': True}
