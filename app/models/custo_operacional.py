"""
Model para Custos Operacionais
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Date, Numeric, Text, ForeignKey
from sqlalchemy.sql import func
from app.models.base import Base


class CustoOperacional(Base):
    """Registro de custos operacionais do sistema"""
    __tablename__ = 'custos_operacionais'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Dados do lançamento
    data_lancamento = Column(Date, nullable=False)
    data_vencimento = Column(Date, nullable=True)
    data_pagamento = Column(Date, nullable=True)

    # Categorização
    categoria = Column(String(100), nullable=False)
    subcategoria = Column(String(100), nullable=True)
    centro_custo = Column(String(100), nullable=True)

    # Descrição e valores
    descricao = Column(Text, nullable=False)
    valor = Column(Numeric(10, 2), nullable=False)
    valor_pago = Column(Numeric(10, 2), nullable=True)

    # Fornecedor
    fornecedor = Column(String(255), nullable=True)
    fornecedor_cnpj = Column(String(18), nullable=True)
    numero_documento = Column(String(100), nullable=True)

    # Comprovante
    comprovante_url = Column(String(500), nullable=True)

    # Recorrência
    recorrencia = Column(String(20), default='unico')
    parcela_atual = Column(Integer, nullable=True)
    total_parcelas = Column(Integer, nullable=True)
    lancamento_pai_id = Column(Integer, ForeignKey('custos_operacionais.id'), nullable=True)

    # Status
    status = Column(String(20), default='pendente')

    # Auditoria
    criado_por = Column(Integer, ForeignKey('usuarios_internos.id'), nullable=True)
    atualizado_por = Column(Integer, ForeignKey('usuarios_internos.id'), nullable=True)
    criado_em = Column(DateTime(timezone=True), server_default=func.now())
    atualizado_em = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Categorias padrão
    CATEGORIAS = [
        'infraestrutura',
        'apis',
        'comunicacao',
        'servicos',
        'marketing',
        'pessoal',
        'impostos',
        'outros'
    ]

    # Recorrências
    RECORRENCIA_UNICO = 'unico'
    RECORRENCIA_MENSAL = 'mensal'
    RECORRENCIA_BIMESTRAL = 'bimestral'
    RECORRENCIA_TRIMESTRAL = 'trimestral'
    RECORRENCIA_SEMESTRAL = 'semestral'
    RECORRENCIA_ANUAL = 'anual'

    RECORRENCIAS = [
        RECORRENCIA_UNICO, RECORRENCIA_MENSAL, RECORRENCIA_BIMESTRAL,
        RECORRENCIA_TRIMESTRAL, RECORRENCIA_SEMESTRAL, RECORRENCIA_ANUAL
    ]

    # Status
    STATUS_PENDENTE = 'pendente'
    STATUS_PAGO = 'pago'
    STATUS_CANCELADO = 'cancelado'
    STATUS_ATRASADO = 'atrasado'

    STATUS_VALIDOS = [STATUS_PENDENTE, STATUS_PAGO, STATUS_CANCELADO, STATUS_ATRASADO]

    def to_dict(self):
        """Converte para dicionário"""
        return {
            'id': self.id,
            'data_lancamento': self.data_lancamento.isoformat() if self.data_lancamento else None,
            'data_vencimento': self.data_vencimento.isoformat() if self.data_vencimento else None,
            'data_pagamento': self.data_pagamento.isoformat() if self.data_pagamento else None,
            'categoria': self.categoria,
            'subcategoria': self.subcategoria,
            'centro_custo': self.centro_custo,
            'descricao': self.descricao,
            'valor': float(self.valor) if self.valor else 0,
            'valor_pago': float(self.valor_pago) if self.valor_pago else None,
            'fornecedor': self.fornecedor,
            'fornecedor_cnpj': self.fornecedor_cnpj,
            'numero_documento': self.numero_documento,
            'comprovante_url': self.comprovante_url,
            'recorrencia': self.recorrencia,
            'parcela_atual': self.parcela_atual,
            'total_parcelas': self.total_parcelas,
            'lancamento_pai_id': self.lancamento_pai_id,
            'status': self.status,
            'criado_por': self.criado_por,
            'atualizado_por': self.atualizado_por,
            'criado_em': self.criado_em.isoformat() if self.criado_em else None,
            'atualizado_em': self.atualizado_em.isoformat() if self.atualizado_em else None
        }

    def __repr__(self):
        return f"<CustoOperacional(id={self.id}, descricao='{self.descricao[:30]}...', valor={self.valor})>"
