"""
Model para Comissionamento Parceiro-Cliente
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Date, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.base import Base


class ComissionamentoParceiro(Base):
    """Registro de comissionamento entre parceiro e cliente"""
    __tablename__ = 'comissionamento_parceiro_cliente'

    id = Column(Integer, primary_key=True, autoincrement=True)
    parceiro_id = Column(Integer, ForeignKey('parceiros_comerciais.id'), nullable=False, index=True)
    cliente_id = Column(Integer, ForeignKey('clientes.id'), nullable=False, index=True)
    data_inicio = Column(Date, nullable=False)
    data_fim = Column(Date, nullable=True)  # null = permanente
    renovado = Column(Boolean, server_default='false', nullable=False)
    data_renovacao = Column(Date, nullable=True)
    observacoes = Column(Text, nullable=True)
    ativo = Column(Boolean, server_default='true', nullable=False)
    criado_em = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relacionamentos
    parceiro = relationship("ParceiroComercial", back_populates="comissionamentos")
    cliente = relationship("Cliente")

    def __repr__(self):
        return f"<ComissionamentoParceiro(parceiro_id={self.parceiro_id}, cliente_id={self.cliente_id}, ativo={self.ativo})>"
