from sqlalchemy import Column, String, Boolean, ForeignKey, Integer, Text
from sqlalchemy.orm import relationship
from .base import BaseModel

class Convenio(BaseModel):
    """Modelo para convênios médicos aceitos pela clínica"""
    __tablename__ = "convenios"
    
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False)
    
    # Dados do convênio
    nome = Column(String(100), nullable=False)  # "Unimed", "Amil", "Particular"
    codigo = Column(String(20), nullable=False)  # "unimed", "amil", "particular"
    ativo = Column(Boolean, default=True, nullable=False)
    observacoes = Column(Text, nullable=True)
    
    # Relacionamentos
    cliente = relationship("Cliente", back_populates="convenios")
    
    def __repr__(self):
        return f"<Convenio(nome='{self.nome}', codigo='{self.codigo}')>"
