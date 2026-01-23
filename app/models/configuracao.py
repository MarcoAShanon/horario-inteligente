from sqlalchemy import Column, String, Boolean, ForeignKey, Integer, Text, JSON
from sqlalchemy.orm import relationship
from .base import BaseModel

class Configuracao(BaseModel):
    """Configurações da clínica (WhatsApp, Google, Anthropic)"""
    __tablename__ = "configuracoes"
    
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False)
    
    # WhatsApp Configuration
    whatsapp_numero = Column(String(20), nullable=True)
    whatsapp_token = Column(String(500), nullable=True)
    evolution_instance_id = Column(String(100), nullable=True)
    whatsapp_ativo = Column(Boolean, default=False)
    
    # Anthropic AI Configuration
    anthropic_api_key = Column(String(200), nullable=True)
    anthropic_model = Column(String(50), default="claude-3-sonnet-20240229")
    anthropic_ativo = Column(Boolean, default=False)
    
    # Configurações do Chat
    mensagem_boas_vindas = Column(Text, default="Olá! 😊 Sou a assistente virtual da clínica. Como posso ajudá-lo hoje?")
    mensagem_despedida = Column(Text, default="Foi um prazer ajudá-lo! Tenha um ótimo dia! 😊")
    horario_funcionamento = Column(JSON, nullable=True)
    # Exemplo: {"inicio": "08:00", "fim": "18:00", "dias": ["seg", "ter", "qua", "qui", "sex"]}
    
    # Timezone
    timezone = Column(String(50), default="America/Sao_Paulo")
    
    # Status geral
    sistema_ativo = Column(Boolean, default=True)
    
    # Relacionamentos
    cliente = relationship("Cliente", back_populates="configuracao")
    
    def __repr__(self):
        return f"<Configuracao(cliente_id={self.cliente_id}, whatsapp_ativo={self.whatsapp_ativo})>"
