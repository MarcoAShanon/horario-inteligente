from sqlalchemy import Column, Integer, Time, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base

class HorarioAtendimento(Base):
    __tablename__ = "horarios_atendimento"
    
    id = Column(Integer, primary_key=True, index=True)
    medico_id = Column(Integer, ForeignKey("medicos.id"))
    dia_semana = Column(Integer)  # 0=Segunda, 1=Terça, etc
    inicio = Column(Time)
    fim = Column(Time)
    ativo = Column(Boolean, default=True)
    
    medico = relationship("Medico", back_populates="horarios")
