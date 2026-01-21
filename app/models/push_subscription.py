"""
Modelo para Push Notifications Subscriptions
Horário Inteligente SaaS

Armazena as subscriptions de push notifications dos médicos para
envio de notificações gratuitas via Web Push API.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime

from .base import BaseModel


class PushSubscription(BaseModel):
    """
    Model para armazenar subscriptions de push notifications.

    Cada médico pode ter múltiplas subscriptions (diferentes navegadores/dispositivos).
    """
    __tablename__ = "push_subscriptions"

    # Relacionamento com médico
    medico_id = Column(Integer, ForeignKey("medicos.id"), nullable=False, index=True)

    # Dados da subscription (Web Push API)
    endpoint = Column(Text, nullable=False, unique=True)  # URL do push service
    p256dh_key = Column(String(255), nullable=False)  # Chave pública do cliente
    auth_key = Column(String(255), nullable=False)  # Chave de autenticação

    # Metadados
    user_agent = Column(String(500), nullable=True)  # Navegador/dispositivo
    ativo = Column(Boolean, default=True, nullable=False)

    # Relacionamento
    medico = relationship("Medico", back_populates="push_subscriptions")

    def __repr__(self):
        return f"<PushSubscription(id={self.id}, medico_id={self.medico_id}, ativo={self.ativo})>"
