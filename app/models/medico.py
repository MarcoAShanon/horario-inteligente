from sqlalchemy import Column, String, Boolean, ForeignKey, Integer, Text, JSON
from sqlalchemy.orm import relationship
from .base import BaseModel

class Medico(BaseModel):
    """Modelo para médicos da clínica"""
    __tablename__ = "medicos"
    
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False)
    
    # Dados pessoais
    nome = Column(String(200), nullable=False)
    crm = Column(String(20), nullable=False)
    especialidade = Column(String(100), nullable=False)
    telefone = Column(String(20), nullable=True)
    email = Column(String(100), nullable=True)
    
    # Horários de atendimento (JSON)
    horarios_atendimento = Column(JSON, nullable=True)
    # Exemplo: {
    #   "segunda": {"inicio": "08:00", "fim": "17:00", "ativo": true},
    #   "terca": {"inicio": "14:00", "fim": "18:00", "ativo": true}
    # }
    
    # Convênios aceitos (lista de códigos)
    convenios_aceitos = Column(JSON, nullable=True)
    # Exemplo: ["unimed", "amil", "particular"]
    
    # Status
    ativo = Column(Boolean, default=True, nullable=False)
    observacoes = Column(Text, nullable=True)

    # Controle de acesso (secretária vs médico)
    is_secretaria = Column(Boolean, default=False, nullable=False)
    pode_ver_financeiro = Column(Boolean, default=True, nullable=False)

    # Relacionamentos
    cliente = relationship("Cliente", back_populates="medicos")
    agendamentos = relationship("Agendamento", back_populates="medico", cascade="all, delete-orphan")
    push_subscriptions = relationship("PushSubscription", back_populates="medico", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Medico(nome='{self.nome}', especialidade='{self.especialidade}')>"
