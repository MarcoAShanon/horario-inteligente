"""
Modelo de Lembrete para Sistema de Lembretes Inteligentes
Horário Inteligente - WhatsApp Business API Oficial

Rastreia lembretes enviados e respostas dos pacientes.
"""

from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Text, Boolean, Enum, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from .base import BaseModel


class TipoLembrete(str, enum.Enum):
    """Tipos de lembrete baseados no tempo antes da consulta"""
    LEMBRETE_24H = "24h"
    LEMBRETE_3H = "3h"
    LEMBRETE_1H = "1h"


class StatusLembrete(str, enum.Enum):
    """Status do lembrete no ciclo de vida"""
    PENDENTE = "pendente"           # Aguardando horário de envio
    ENVIADO = "enviado"             # Enviado, aguardando resposta
    CONFIRMADO = "confirmado"       # Paciente confirmou presença
    REMARCAR = "remarcar"           # Paciente quer remarcar
    CANCELAR = "cancelar"           # Paciente quer cancelar
    SEM_RESPOSTA = "sem_resposta"   # Não respondeu até a consulta
    ERRO = "erro"                   # Erro no envio


class Lembrete(BaseModel):
    """
    Modelo para rastrear lembretes de consultas.

    Um agendamento pode ter múltiplos lembretes (24h, 3h, 1h).
    Cada lembrete rastreia seu status e resposta do paciente.
    """
    __tablename__ = "lembretes"
    __table_args__ = (
        UniqueConstraint('agendamento_id', 'tipo', name='uq_lembrete_agendamento_tipo'),
    )

    # Relacionamento com agendamento
    agendamento_id = Column(Integer, ForeignKey("agendamentos.id"), nullable=False)

    # Tipo e status
    tipo = Column(String(10), nullable=False)  # 24h, 3h, 1h
    status = Column(String(20), default="pendente", nullable=False)

    # Dados do envio
    enviado_em = Column(DateTime(timezone=True), nullable=True)
    message_id = Column(String(100), nullable=True)  # ID da mensagem no WhatsApp
    template_usado = Column(String(100), nullable=True)  # Nome do template Meta

    # Resposta do paciente
    respondido_em = Column(DateTime(timezone=True), nullable=True)
    resposta_texto = Column(Text, nullable=True)  # Texto original do paciente
    intencao_detectada = Column(String(50), nullable=True)  # confirmar, remarcar, cancelar, duvida

    # Controle de reenvio
    tentativas_envio = Column(Integer, default=0)
    ultimo_erro = Column(Text, nullable=True)

    # Flag para lembrete de 1h solicitado pelo paciente
    lembrete_1h_solicitado = Column(Boolean, default=False)

    # Relacionamentos
    agendamento = relationship("Agendamento", backref="lembretes")

    def __repr__(self):
        return f"<Lembrete(id={self.id}, tipo={self.tipo}, status={self.status}, agendamento_id={self.agendamento_id})>"

    @property
    def foi_enviado(self) -> bool:
        """Verifica se o lembrete já foi enviado"""
        return self.status != StatusLembrete.PENDENTE.value

    @property
    def aguardando_resposta(self) -> bool:
        """Verifica se está aguardando resposta do paciente"""
        return self.status == StatusLembrete.ENVIADO.value

    def marcar_enviado(self, message_id: str = None, template: str = None):
        """Marca o lembrete como enviado"""
        self.status = StatusLembrete.ENVIADO.value
        self.enviado_em = datetime.utcnow()
        self.message_id = message_id
        self.template_usado = template
        self.tentativas_envio += 1

    def registrar_resposta(self, texto: str, intencao: str):
        """Registra a resposta do paciente"""
        self.respondido_em = datetime.utcnow()
        self.resposta_texto = texto
        self.intencao_detectada = intencao

        # Atualizar status baseado na intenção
        if intencao == "confirmar":
            self.status = StatusLembrete.CONFIRMADO.value
        elif intencao == "remarcar":
            self.status = StatusLembrete.REMARCAR.value
        elif intencao == "cancelar":
            self.status = StatusLembrete.CANCELAR.value
        # Se for "duvida" ou outro, mantém como ENVIADO para continuar conversa

    def marcar_erro(self, erro: str):
        """Marca erro no envio"""
        self.status = StatusLembrete.ERRO.value
        self.ultimo_erro = erro
        self.tentativas_envio += 1
