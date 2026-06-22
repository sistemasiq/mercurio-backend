from sqlalchemy import Column, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship

from app.db.database import Base


class PaqueteTipoEventoModel(Base):
    """Tabla intermedia: qué tipos de evento acepta cada paquete."""

    __tablename__ = "paquete_tipos_evento"

    paquete_id = Column(PGUUID(as_uuid=True), ForeignKey("paquetes.id"), primary_key=True)
    tipo_evento_id = Column(PGUUID(as_uuid=True), ForeignKey("tipos_evento.id"), primary_key=True)

    paquete = relationship("PaqueteModel", back_populates="paquete_tipos_evento")
    tipo_evento = relationship("TipoEventoModel", back_populates="paquete_tipos_evento")
