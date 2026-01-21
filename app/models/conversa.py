"""
Model de Conversa WhatsApp
Horário Inteligente SaaS

Persiste conversas do WhatsApp para histórico e gestão de atendimento.
Inclui sistema de detecção e classificação de urgência.
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, Index, Boolean, Text
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from .base import BaseModel


class StatusConversa(str, enum.Enum):
    """Status da conversa"""
    IA_ATIVA = "ia_ativa"           # IA está respondendo
    HUMANO_ASSUMIU = "humano_assumiu"  # Atendente humano assumiu
    ENCERRADA = "encerrada"         # Conversa encerrada


class NivelUrgencia(str, enum.Enum):
    """Nível de urgência da conversa"""
    NORMAL = "normal"       # Fluxo normal de agendamento
    ATENCAO = "atencao"     # Situação que merece atenção do médico
    CRITICA = "critica"     # Emergência - notificar médico imediatamente


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
    atendente_id = Column(Integer, nullable=True)  # ID do atendente (médico ou secretária)
    atendente_tipo = Column(String(20), nullable=True)  # "medico" ou "secretaria"

    # Sistema de Urgência - usando values_callable para mapear valores lowercase do banco
    urgencia_nivel = Column(
        Enum(NivelUrgencia, values_callable=lambda obj: [e.value for e in obj]),
        default=NivelUrgencia.NORMAL,
        nullable=False
    )
    urgencia_detectada_em = Column(DateTime, nullable=True)  # Quando a urgência foi detectada
    urgencia_resolvida = Column(Boolean, default=True, nullable=False)  # Se a urgência foi tratada
    urgencia_motivo = Column(Text, nullable=True)  # Descrição do motivo da urgência

    # Timestamps
    ultima_mensagem_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    closed_at = Column(DateTime, nullable=True)

    # Relacionamentos
    cliente = relationship("Cliente", back_populates="conversas")
    mensagens = relationship("Mensagem", back_populates="conversa", order_by="Mensagem.timestamp", cascade="all, delete-orphan")

    # Índice composto para busca rápida por cliente + telefone
    __table_args__ = (
        Index('ix_conversa_cliente_telefone', 'cliente_id', 'paciente_telefone'),
    )

    def __repr__(self):
        return f"<Conversa(id={self.id}, telefone='{self.paciente_telefone}', status='{self.status}')>"
