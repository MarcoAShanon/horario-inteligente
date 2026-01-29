# app/models/calendario.py
# Models para sistema de calendário próprio
# Marco - Sistema Horário Inteligente
#
# NOTA: BloqueioAgenda foi movido para configuracoes.py (versão mais completa)

from sqlalchemy import Column, Integer, String, Boolean, Time, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base

class HorarioAtendimento(Base):
    __tablename__ = "horarios_atendimento"

    id = Column(Integer, primary_key=True, index=True)
    medico_id = Column(Integer, ForeignKey("medicos.id"), nullable=False)
    dia_semana = Column(Integer, nullable=False)  # 1=Segunda, 2=Terça, etc.
    hora_inicio = Column(Time, nullable=False)
    hora_fim = Column(Time, nullable=False)
    ativo = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.current_timestamp())

# BloqueioAgenda removido - usar app.models.configuracoes.BloqueioAgenda

