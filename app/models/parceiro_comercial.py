"""
Model para Parceiros Comerciais (Indicadores/Afiliados)
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Numeric, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
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

    # Recorrência de comissão
    recorrencia_comissao_meses = Column(Integer, nullable=True)  # null = permanente
    recorrencia_renovavel = Column(Boolean, server_default='true', nullable=False)

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

    # Status do parceiro
    status = Column(String(30), server_default='ativo', nullable=False)  # 'pendente_aceite', 'ativo', 'suspenso', 'inativo'

    # Autenticação do portal do parceiro
    senha_hash = Column(String(255), nullable=True)
    token_login = Column(String(255), nullable=True)
    ultimo_login = Column(DateTime(timezone=True), nullable=True)

    # Token de ativação
    token_ativacao = Column(String(100), nullable=True, unique=True)
    token_expira_em = Column(DateTime(timezone=True), nullable=True)

    # Aceite do termo de parceria
    aceite_termo_em = Column(DateTime(timezone=True), nullable=True)
    aceite_termo_ip = Column(String(45), nullable=True)
    aceite_termo_user_agent = Column(Text, nullable=True)
    aceite_termo_versao = Column(String(20), nullable=True)

    # Tipos de comissão
    TIPO_PERCENTUAL = 'percentual'
    TIPO_FIXO = 'fixo'
    TIPO_PERCENTUAL_MARGEM = 'percentual_margem'

    # Relacionamentos
    aceites_termo = relationship("HistoricoAceiteParceiro", back_populates="parceiro")
    comissionamentos = relationship("ComissionamentoParceiro", back_populates="parceiro")

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
            'recorrencia_comissao_meses': self.recorrencia_comissao_meses,
            'recorrencia_renovavel': self.recorrencia_renovavel,
            'parceria_lancamento': self.parceria_lancamento,
            'limite_clientes_lancamento': self.limite_clientes_lancamento,
            'dados_bancarios': self.dados_bancarios,
            'observacoes': self.observacoes,
            'status': self.status,
            'ativo': self.ativo,
            'aceite_termo_em': self.aceite_termo_em.isoformat() if self.aceite_termo_em else None,
            'aceite_termo_versao': self.aceite_termo_versao,
            'criado_em': self.criado_em.isoformat() if self.criado_em else None,
            'atualizado_em': self.atualizado_em.isoformat() if self.atualizado_em else None
        }

    def __repr__(self):
        return f"<ParceiroComercial(id={self.id}, nome='{self.nome}', comissao={self.percentual_comissao}%)>"
