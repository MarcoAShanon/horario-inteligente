from sqlalchemy import Column, String, Date, ForeignKey, Integer, Text
from sqlalchemy.orm import relationship
from .base import BaseModel

class Paciente(BaseModel):
    """Modelo para pacientes da clínica"""
    __tablename__ = "pacientes"
    
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False)
    
    # Dados pessoais
    nome = Column(String(200), nullable=False)
    telefone = Column(String(20), nullable=False, unique=True)
    email = Column(String(100), nullable=True)
    data_nascimento = Column(Date, nullable=True)
    cpf = Column(String(14), nullable=True)
    
    # Convênio
    convenio = Column(String(50), nullable=False, default="particular")  # unimed, amil, particular
    numero_carteira = Column(String(50), nullable=True)  # Número da carteirinha do convênio
    
    # Endereço
    endereco = Column(Text, nullable=True)
    
    # Observações médicas
    observacoes = Column(Text, nullable=True)
    
    # Relacionamentos
    cliente = relationship("Cliente", back_populates="pacientes")
    agendamentos = relationship("Agendamento", back_populates="paciente", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Paciente(nome='{self.nome}', convenio='{self.convenio}')>"
