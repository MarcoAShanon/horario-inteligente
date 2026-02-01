"""
Model de Mensagem WhatsApp
Horário Inteligente SaaS

Persiste mensagens individuais das conversas do WhatsApp.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from .base import BaseModel


class DirecaoMensagem(str, enum.Enum):
    """Direção da mensagem"""
    ENTRADA = "entrada"  # Paciente enviou
    SAIDA = "saida"      # Sistema/atendente enviou


class RemetenteMensagem(str, enum.Enum):
    """Quem enviou a mensagem"""
    PACIENTE = "paciente"
    IA = "ia"
    ATENDENTE = "atendente"
    SISTEMA = "sistema"


class TipoMensagem(str, enum.Enum):
    """Tipo de conteúdo da mensagem"""
    TEXTO = "texto"
    AUDIO = "audio"
    IMAGEM = "imagem"
    DOCUMENTO = "documento"


class Mensagem(BaseModel):
    """
    Model para mensagens individuais do WhatsApp.

    Cada mensagem pertence a uma conversa e pode ser de diferentes tipos
    (texto, áudio, imagem, documento) e remetentes (paciente, IA, atendente).
    """
    __tablename__ = "mensagens"

    # Relacionamento com conversa
    conversa_id = Column(Integer, ForeignKey("conversas.id"), nullable=False, index=True)

    # Dados da mensagem
    direcao = Column(Enum(DirecaoMensagem), nullable=False)
    remetente = Column(Enum(RemetenteMensagem), nullable=False)
    tipo = Column(Enum(TipoMensagem), default=TipoMensagem.TEXTO, nullable=False)
    conteudo = Column(Text, nullable=False)

    # Mídia (para áudio, imagem, documento)
    midia_url = Column(String(500), nullable=True)

    # Status
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    lida = Column(Boolean, default=False, nullable=False)

    # Relacionamento
    conversa = relationship("Conversa", back_populates="mensagens")

    def __repr__(self):
        return f"<Mensagem(id={self.id}, remetente='{self.remetente}', tipo='{self.tipo}')>"
