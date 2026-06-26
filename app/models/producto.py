from sqlalchemy import Column, String, Numeric, Boolean, Enum, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.core.database import Base
from app.models.enums import tipo_producto

class Producto(Base):
    __tablename__ = "productos"

    id = Column(String, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False, unique=True)
    precio_unitario = Column(Numeric(10, 2), nullable=False)
    tipo = Column(String, nullable=False)
    
    # Campos que faltaban
    descripcion = Column(String, nullable=True) 
    imagen = Column(String(255), nullable=True)
    
    # Relación de sucursal
    sucursal_id = Column(String, nullable=False) # Si es UUID en DB, String es correcto en SQLAlchemy
    
    # Auditoría
    activo = Column(Boolean, default=True)
    creado = Column(DateTime(timezone=True), server_default=func.now())
    creado_por = Column(String, nullable=True)
    modificado = Column(DateTime(timezone=True), nullable=True)
    modificado_por = Column(String, nullable=True)