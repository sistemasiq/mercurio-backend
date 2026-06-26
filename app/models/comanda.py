# app/models/comanda.py
from sqlalchemy import Column, String, Numeric, DateTime, ForeignKey, SmallInteger, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
from app.models.enums import EstadoComanda

class Comanda(Base):
    __tablename__ = "comandas"

    id = Column(String, primary_key=True, index=True)
    ticket_numero = Column(String(10), nullable=False)
    # Usamos solo este campo para la fecha
    fecha_hora = Column(DateTime(timezone=True), server_default=func.now())
    
    estado_actual = Column(String, default=EstadoComanda.PENDIENTE.value, nullable=False) 
    total_final = Column(Numeric(10, 2), default=0.00)
    sucursal_id = Column(String, nullable=False)

    
    # Relación uno a muchos
    detalles = relationship("DetalleComanda", back_populates="comanda")

class DetalleComanda(Base):
    __tablename__ = "detalles_comanda"

    id = Column(String, primary_key=True, index=True)
    comanda_id = Column(String, ForeignKey("comandas.id"), nullable=False)
    producto_id = Column(String, ForeignKey("productos.id"), nullable=False)
    cantidad = Column(SmallInteger, nullable=False)
    precio_unitario = Column(Numeric(10, 2), nullable=False)
    importe = Column(Numeric(10, 2), nullable=False)
    sucursal_id = Column(String, nullable=False)
    notas_especiales = Column(String, nullable=True)
    producto = relationship("Producto")
    # Relación inversa
    comanda = relationship("Comanda", back_populates="detalles")