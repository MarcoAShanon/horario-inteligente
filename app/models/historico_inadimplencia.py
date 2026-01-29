"""
Modelo de Historico de Inadimplencia
Registra eventos de suspensao e reativacao de clientes por inadimplencia
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .base import Base


class HistoricoInadimplencia(Base):
    __tablename__ = "historico_inadimplencia"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cliente_id = Column(Integer, ForeignKey('clientes.id'), nullable=False, index=True)
    asaas_payment_id = Column(String(50), nullable=True)
    evento = Column(String(30), nullable=False, index=True)  # SUSPENSAO, REATIVACAO
    data_evento = Column(DateTime, server_default=func.now(), nullable=False)
    observacoes = Column(Text, nullable=True)

    # Relacionamentos
    cliente = relationship("Cliente", backref="historico_inadimplencia")

    def __repr__(self):
        return f"<HistoricoInadimplencia cliente_id={self.cliente_id} evento={self.evento}>"
