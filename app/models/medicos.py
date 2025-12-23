from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class Medico(Base):
    __tablename__ = "medicos"
    
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100), nullable=False)
    especialidade = Column(String(100))
    email = Column(String(100), unique=True)
    telefone = Column(String(20))
    ativo = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relacionamentos
    configuracoes = relationship("ConfiguracoesMedico", back_populates="medico", uselist=False)
