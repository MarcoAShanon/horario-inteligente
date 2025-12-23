"""
Model para relacionamento Cliente-Parceiro
"""
from sqlalchemy import Column, Integer, Boolean, DateTime, Date, Numeric, Text, ForeignKey, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.base import Base


class ClienteParceiro(Base):
    """Relacionamento entre clientes e parceiros comerciais"""
    __tablename__ = 'clientes_parceiros'

    id = Column(Integer, primary_key=True, autoincrement=True)
    cliente_id = Column(Integer, ForeignKey('clientes.id', ondelete='CASCADE'), nullable=False)
    parceiro_id = Column(Integer, ForeignKey('parceiros_comerciais.id', ondelete='CASCADE'), nullable=False)

    # Datas do vínculo
    data_vinculo = Column(Date, nullable=False)
    data_desvinculo = Column(Date, nullable=True)

    # Override de comissão para este cliente específico
    percentual_comissao_override = Column(Numeric(5, 2), nullable=True)

    # Controle de parceria estratégica
    tipo_parceria = Column(String(30), default='padrao')  # 'padrao', 'lancamento'
    ordem_cliente = Column(Integer, nullable=True)  # Número sequencial do cliente (1-40 para lançamento)
    comissao_sobre = Column(String(20), default='receita')  # 'receita', 'margem'

    observacoes = Column(Text, nullable=True)
    ativo = Column(Boolean, default=True)
    criado_em = Column(DateTime(timezone=True), server_default=func.now())
    atualizado_em = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def to_dict(self):
        """Converte para dicionário"""
        return {
            'id': self.id,
            'cliente_id': self.cliente_id,
            'parceiro_id': self.parceiro_id,
            'data_vinculo': self.data_vinculo.isoformat() if self.data_vinculo else None,
            'data_desvinculo': self.data_desvinculo.isoformat() if self.data_desvinculo else None,
            'percentual_comissao_override': float(self.percentual_comissao_override) if self.percentual_comissao_override else None,
            'tipo_parceria': self.tipo_parceria,
            'ordem_cliente': self.ordem_cliente,
            'comissao_sobre': self.comissao_sobre,
            'observacoes': self.observacoes,
            'ativo': self.ativo,
            'criado_em': self.criado_em.isoformat() if self.criado_em else None,
            'atualizado_em': self.atualizado_em.isoformat() if self.atualizado_em else None
        }

    def __repr__(self):
        return f"<ClienteParceiro(cliente_id={self.cliente_id}, parceiro_id={self.parceiro_id})>"
