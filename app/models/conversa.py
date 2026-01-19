"""
Model de Conversa WhatsApp
Horário Inteligente SaaS

Persiste conversas do WhatsApp para histórico e gestão de atendimento.
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, Index
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from .base import BaseModel


class StatusConversa(str, enum.Enum):
    """Status da conversa"""
    IA_ATIVA = "ia_ativa"           # IA está respondendo
    HUMANO_ASSUMIU = "humano_assumiu"  # Atendente humano assumiu
    ENCERRADA = "encerrada"         # Conversa encerrada


class Conversa(BaseModel):
    """
    Model para conversas do WhatsApp.

    Cada conversa representa uma sessão de chat com um paciente.
    Pode ser atendida pela IA ou por um atendente humano.
    """
    __tablename__ = "conversas"

    # Relacionamento com cliente (multi-tenant)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False)

    # Dados do paciente
    paciente_telefone = Column(String(20), nullable=False, index=True)
    paciente_nome = Column(String(100), nullable=True)  # Preenchido quando identificado

    # Status e atendimento
    status = Column(Enum(StatusConversa), default=StatusConversa.IA_ATIVA, nullable=False)
    atendente_id = Column(Integer, ForeignKey("medicos.id"), nullable=True)  # Quem assumiu

    # Timestamps
    ultima_mensagem_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    closed_at = Column(DateTime, nullable=True)

    # Relacionamentos
    cliente = relationship("Cliente", back_populates="conversas")
    mensagens = relationship("Mensagem", back_populates="conversa", order_by="Mensagem.timestamp", cascade="all, delete-orphan")
    atendente = relationship("Medico", foreign_keys=[atendente_id])

    # Índice composto para busca rápida por cliente + telefone
    __table_args__ = (
        Index('ix_conversa_cliente_telefone', 'cliente_id', 'paciente_telefone'),
    )

    def __repr__(self):
        return f"<Conversa(id={self.id}, telefone='{self.paciente_telefone}', status='{self.status}')>"
