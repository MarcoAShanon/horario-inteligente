"""
Model para Comissões de Parceiros Comerciais
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Date, Numeric, Text, ForeignKey
from sqlalchemy.sql import func
from app.models.base import Base


class Comissao(Base):
    """Comissões geradas para parceiros comerciais"""
    __tablename__ = 'comissoes'

    id = Column(Integer, primary_key=True, autoincrement=True)
    parceiro_id = Column(Integer, ForeignKey('parceiros_comerciais.id', ondelete='CASCADE'), nullable=False)
    cliente_id = Column(Integer, ForeignKey('clientes.id', ondelete='CASCADE'), nullable=False)
    assinatura_id = Column(Integer, ForeignKey('assinaturas.id', ondelete='SET NULL'), nullable=True)

    # Valores da comissão
    valor_base = Column(Numeric(10, 2), nullable=False)  # Valor base usado para cálculo (valor_com_desconto)
    percentual_aplicado = Column(Numeric(5, 2), nullable=False)  # Percentual aplicado
    valor_comissao = Column(Numeric(10, 2), nullable=False)  # Valor final da comissão

    # Referência temporal
    mes_referencia = Column(Integer, nullable=True)  # 1 = primeira mensalidade, 2 = segunda, etc.
    data_referencia = Column(Date, nullable=True)  # Data de referência da comissão

    # Status e pagamento
    status = Column(String(20), default='pendente')  # pendente, aprovada, paga, cancelada
    data_pagamento = Column(DateTime, nullable=True)
    asaas_transfer_id = Column(String(100), nullable=True)  # ID da transferência no ASAAS
    comprovante_url = Column(String(500), nullable=True)

    observacoes = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    # Constantes de status
    STATUS_PENDENTE = 'pendente'
    STATUS_APROVADA = 'aprovada'
    STATUS_PAGA = 'paga'
    STATUS_CANCELADA = 'cancelada'

    def to_dict(self):
        """Converte para dicionário"""
        return {
            'id': self.id,
            'parceiro_id': self.parceiro_id,
            'cliente_id': self.cliente_id,
            'assinatura_id': self.assinatura_id,
            'valor_base': float(self.valor_base) if self.valor_base else 0,
            'percentual_aplicado': float(self.percentual_aplicado) if self.percentual_aplicado else 0,
            'valor_comissao': float(self.valor_comissao) if self.valor_comissao else 0,
            'mes_referencia': self.mes_referencia,
            'data_referencia': self.data_referencia.isoformat() if self.data_referencia else None,
            'status': self.status,
            'data_pagamento': self.data_pagamento.isoformat() if self.data_pagamento else None,
            'asaas_transfer_id': self.asaas_transfer_id,
            'comprovante_url': self.comprovante_url,
            'observacoes': self.observacoes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def __repr__(self):
        return f"<Comissao(id={self.id}, parceiro={self.parceiro_id}, valor={self.valor_comissao}, status={self.status})>"
