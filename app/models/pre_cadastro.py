"""
Modelo de Pré-Cadastro para Lançamento
Sistema Horário Inteligente
"""
from sqlalchemy import Column, String, Boolean, Text, DateTime
from sqlalchemy.sql import func
from .base import BaseModel


class PreCadastro(BaseModel):
    """Modelo para leads de pré-lançamento"""
    __tablename__ = "pre_cadastros"

    # Dados pessoais
    nome = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, unique=True, index=True)
    whatsapp = Column(String(20), nullable=False)

    # Dados profissionais
    profissao = Column(String(100), nullable=False)
    cidade_estado = Column(String(255), nullable=False)

    # Sistema atual
    usa_sistema = Column(String(255), nullable=True)
    nome_sistema_atual = Column(String(255), nullable=True)

    # Marketing
    origem = Column(String(100), nullable=True)

    # Consentimento
    aceite_comunicacao = Column(Boolean, default=True, nullable=False)

    # Metadados
    data_cadastro = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    status = Column(String(50), default="pendente", nullable=False)  # pendente, confirmado, convertido
    ip_origem = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)

    def __repr__(self):
        return f"<PreCadastro(nome='{self.nome}', email='{self.email}', status='{self.status}')>"
