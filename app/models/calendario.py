# app/models/calendario.py
# Models para sistema de calendário próprio
# Marco - Sistema Horário Inteligente

from sqlalchemy import Column, Integer, String, Boolean, Time, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class HorarioAtendimento(Base):
    __tablename__ = "horarios_atendimento"
    
    id = Column(Integer, primary_key=True, index=True)
    medico_id = Column(Integer, ForeignKey("medicos.id"), nullable=False)
    dia_semana = Column(Integer, nullable=False)  # 1=Segunda, 2=Terça, etc.
    hora_inicio = Column(Time, nullable=False)
    hora_fim = Column(Time, nullable=False)
    ativo = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.current_timestamp())

class BloqueioAgenda(Base):
    __tablename__ = "bloqueios_agenda"
    
    id = Column(Integer, primary_key=True, index=True)
    medico_id = Column(Integer, ForeignKey("medicos.id"), nullable=False)
    data_inicio = Column(DateTime, nullable=False)
    data_fim = Column(DateTime, nullable=False)
    motivo = Column(String(255), nullable=False)
    tipo = Column(String(50), default="bloqueio")
    ativo = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.current_timestamp())

