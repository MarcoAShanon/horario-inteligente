"""
Model para Parceiros Comerciais (Indicadores/Afiliados)
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Numeric, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from app.models.base import Base


class ParceiroComercial(Base):
    """Parceiros comerciais que indicam clientes"""
    __tablename__ = 'parceiros_comerciais'

    id = Column(Integer, primary_key=True, autoincrement=True)
    nome = Column(String(255), nullable=False)
    tipo_pessoa = Column(String(2), default='PJ')  # PF ou PJ
    cpf_cnpj = Column(String(18), nullable=True)
    email = Column(String(255), nullable=True)
    telefone = Column(String(20), nullable=True)
    endereco = Column(Text, nullable=True)

    # Dados de comissão
    percentual_comissao = Column(Numeric(5, 2), default=0)
    valor_fixo_comissao = Column(Numeric(10, 2), nullable=True)
    tipo_comissao = Column(String(30), default='percentual')  # 'percentual', 'fixo', 'percentual_margem'

    # Parceria estratégica de lançamento
    parceria_lancamento = Column(Boolean, default=False)
    limite_clientes_lancamento = Column(Integer, default=40)

    # Dados bancários para pagamento
    dados_bancarios = Column(JSONB, nullable=True)
    # Estrutura esperada:
    # {
    #   "banco": "341",
    #   "agencia": "1234",
    #   "conta": "12345-6",
    #   "tipo_conta": "corrente",
    #   "titular": "Nome do Titular",
    #   "cpf_cnpj_titular": "12345678901",
    #   "pix": "email@example.com"
    # }

    observacoes = Column(Text, nullable=True)
    ativo = Column(Boolean, default=True)
    criado_em = Column(DateTime(timezone=True), server_default=func.now())
    atualizado_em = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Tipos de comissão
    TIPO_PERCENTUAL = 'percentual'
    TIPO_FIXO = 'fixo'
    TIPO_PERCENTUAL_MARGEM = 'percentual_margem'

    def to_dict(self):
        """Converte para dicionário"""
        return {
            'id': self.id,
            'nome': self.nome,
            'tipo_pessoa': self.tipo_pessoa,
            'cpf_cnpj': self.cpf_cnpj,
            'email': self.email,
            'telefone': self.telefone,
            'endereco': self.endereco,
            'percentual_comissao': float(self.percentual_comissao) if self.percentual_comissao else 0,
            'valor_fixo_comissao': float(self.valor_fixo_comissao) if self.valor_fixo_comissao else None,
            'tipo_comissao': self.tipo_comissao,
            'parceria_lancamento': self.parceria_lancamento,
            'limite_clientes_lancamento': self.limite_clientes_lancamento,
            'dados_bancarios': self.dados_bancarios,
            'observacoes': self.observacoes,
            'ativo': self.ativo,
            'criado_em': self.criado_em.isoformat() if self.criado_em else None,
            'atualizado_em': self.atualizado_em.isoformat() if self.atualizado_em else None
        }

    def __repr__(self):
        return f"<ParceiroComercial(id={self.id}, nome='{self.nome}', comissao={self.percentual_comissao}%)>"
