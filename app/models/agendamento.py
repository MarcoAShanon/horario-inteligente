from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Text, Boolean
from sqlalchemy.orm import relationship
from .base import BaseModel

class Agendamento(BaseModel):
    """Modelo para agendamentos médicos"""
    __tablename__ = "agendamentos"
    
    # Relacionamentos
    paciente_id = Column(Integer, ForeignKey("pacientes.id"), nullable=False)
    medico_id = Column(Integer, ForeignKey("medicos.id"), nullable=False)
    
    # Dados do agendamento
    data_hora = Column(DateTime(timezone=True), nullable=False)
    status = Column(String(50), default="agendado", nullable=False)
    # Status: agendado, confirmado, cancelado, realizado, faltou
    
    # Tipo de atendimento
    tipo_atendimento = Column(String(50), nullable=False)  # convenio ou particular
    valor_consulta = Column(String(10), nullable=True)  # Valor se particular
    
    # Integração Google Calendar
    evento_calendar_id = Column(String(200), nullable=True)  # ID do evento no Google Calendar
    
    # Observações
    motivo_consulta = Column(Text, nullable=True)
    observacoes = Column(Text, nullable=True)
    observacoes_medico = Column(Text, nullable=True)
    
    # Controle de lembretes
    lembrete_24h_enviado = Column(Boolean, default=False)
    lembrete_3h_enviado = Column(Boolean, default=False)
    lembrete_1h_enviado = Column(Boolean, default=False)
    
    # Relacionamentos
    paciente = relationship("Paciente", back_populates="agendamentos")
    medico = relationship("Medico", back_populates="agendamentos")
    
    def __repr__(self):
        return f"<Agendamento(paciente='{self.paciente.nome if self.paciente else 'N/A'}', medico='{self.medico.nome if self.medico else 'N/A'}', data='{self.data_hora}')>"
