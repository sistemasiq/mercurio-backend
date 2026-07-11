from uuid import uuid4
from sqlalchemy import Column, String, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
from app.database import Base

class PaqueteTiposEventoModel(Base):
    __tablename__ = "paquete_tipos_evento"

    paquete_id = Column(PG_UUID(as_uuid=True), ForeignKey("paquetes.id"), nullable=False)
    tipo_evento_id = Column(PG_UUID(as_uuid=True), ForeignKey("tipos_evento.id"), nullable=False)

    paquete = relationship("Paquete", back_populates="paquete_tipos_evento")
    tipo_evento = relationship("TiposEvento", back_populates="paquete_tipos_evento")