"""
Model de Alerta de Urgência
Horário Inteligente SaaS

Registra histórico de alertas de urgência detectados em conversas WhatsApp.
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, Text, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime

from .base import BaseModel
from .conversa import NivelUrgencia


class AlertaUrgencia(BaseModel):
    """
    Model para alertas de urgência detectados.

    Cada alerta representa uma detecção de urgência em uma conversa,
    permitindo rastrear histórico e métricas de urgências.
    """
    __tablename__ = "alertas_urgencia"

    # Relacionamentos
    conversa_id = Column(Integer, ForeignKey("conversas.id"), nullable=False, index=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False, index=True)
    medico_id = Column(Integer, ForeignKey("medicos.id"), nullable=True)  # Médico responsável

    # Dados do alerta
    nivel = Column(Enum(NivelUrgencia), nullable=False)
    motivo = Column(Text, nullable=False)  # Descrição/motivo detectado pela IA
    mensagem_gatilho = Column(Text, nullable=True)  # Mensagem que disparou o alerta
    paciente_telefone = Column(String(20), nullable=False)
    paciente_nome = Column(String(100), nullable=True)

    # Status do alerta
    notificacao_enviada = Column(Boolean, default=False, nullable=False)
    visualizado = Column(Boolean, default=False, nullable=False)
    visualizado_em = Column(DateTime, nullable=True)
    visualizado_por = Column(Integer, nullable=True)  # ID do usuário que visualizou

    # Resolução
    resolvido = Column(Boolean, default=False, nullable=False)
    resolvido_em = Column(DateTime, nullable=True)
    resolvido_por = Column(Integer, nullable=True)  # ID do usuário que resolveu
    resolucao_nota = Column(Text, nullable=True)  # Nota sobre a resolução

    # Relacionamentos
    conversa = relationship("Conversa", backref="alertas_urgencia")

    def __repr__(self):
        return f"<AlertaUrgencia(id={self.id}, nivel='{self.nivel}', conversa_id={self.conversa_id})>"
