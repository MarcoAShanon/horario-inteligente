"""
Modelo de Plano de Assinatura
Representa os planos disponíveis (Individual, Clínica)
"""
from sqlalchemy import Column, Integer, String, Text, Numeric, Boolean, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class Plano(Base):
    __tablename__ = "planos"

    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(50), unique=True, nullable=False)  # 'individual', 'clinica'
    nome = Column(String(100), nullable=False)
    descricao = Column(Text)
    valor_mensal = Column(Numeric(10, 2), nullable=False)
    profissionais_inclusos = Column(Integer, default=1)
    valor_profissional_adicional = Column(Numeric(10, 2), default=50.00)
    taxa_ativacao = Column(Numeric(10, 2), default=150.00)
    ativo = Column(Boolean, default=True)
    criado_em = Column(DateTime, server_default=func.now())
    atualizado_em = Column(DateTime, onupdate=func.now())

    # Relacionamentos
    assinaturas = relationship("Assinatura", back_populates="plano")

    def calcular_valor_total(self, profissionais_adicionais: int = 0) -> float:
        """Calcula valor total mensal com profissionais adicionais"""
        return float(self.valor_mensal) + (profissionais_adicionais * float(self.valor_profissional_adicional))

    def __repr__(self):
        return f"<Plano {self.codigo}: R$ {self.valor_mensal}>"
