from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime
from sqlalchemy.orm import relationship
from .base import BaseModel

class Cliente(BaseModel):
    """Modelo para clínicas (clientes do SaaS)"""
    __tablename__ = "clientes"

    # Dados da clínica
    nome = Column(String(200), nullable=False)
    cnpj = Column(String(18), unique=True, nullable=True)
    email = Column(String(100), nullable=False)
    telefone = Column(String(20), nullable=True)
    endereco = Column(Text, nullable=True)

    # Multi-tenant (NOVO)
    subdomain = Column(String(100), unique=True, nullable=True, index=True)  # drmarco, drjoao, etc
    whatsapp_instance = Column(String(100), nullable=True)  # Nome da instância Evolution API
    whatsapp_numero = Column(String(20), nullable=True)  # Número WhatsApp da clínica
    whatsapp_phone_number_id = Column(String(50), nullable=True, index=True)  # Phone Number ID da Meta

    # Branding e Identidade Visual (NOVO - v3.4.0)
    logo_url = Column(String(500), nullable=True)  # URL da logo (ex: /static/logos/clinica.png)
    logo_icon = Column(String(100), default="fa-heartbeat", nullable=False)  # Ícone FontAwesome
    cor_primaria = Column(String(7), default="#3b82f6", nullable=False)  # Cor primária (hex)
    cor_secundaria = Column(String(7), default="#1e40af", nullable=False)  # Cor secundária (hex)
    favicon_url = Column(String(500), nullable=True)  # URL do favicon

    # Configurações do plano
    plano = Column(String(50), default="basico", nullable=False)  # basico, profissional, enterprise
    ativo = Column(Boolean, default=True, nullable=False)
    is_demo = Column(Boolean, default=False, nullable=False)
    valor_mensalidade = Column(String(10), default="150.00", nullable=False)

    # ASAAS Integration
    asaas_customer_id = Column(String(50), nullable=True, index=True)  # ID do cliente no ASAAS

    # Status de onboarding
    status = Column(String(30), default="ativo", nullable=False)  # pendente_aceite, ativo, aguardando_pagamento, suspenso, cancelado

    # Token de ativação
    token_ativacao = Column(String(100), nullable=True, unique=True, index=True)
    token_expira_em = Column(DateTime(timezone=True), nullable=True)

    # Quem cadastrou
    cadastrado_por_id = Column(Integer, nullable=True)
    cadastrado_por_tipo = Column(String(20), nullable=True)  # 'admin', 'parceiro'

    # Aceite de termos
    aceite_termos_em = Column(DateTime(timezone=True), nullable=True)
    aceite_ip = Column(String(45), nullable=True)
    aceite_user_agent = Column(Text, nullable=True)
    aceite_versao_termos = Column(String(10), nullable=True)
    aceite_versao_privacidade = Column(String(10), nullable=True)

    # Credenciais enviadas
    credenciais_enviadas_em = Column(DateTime(timezone=True), nullable=True)

    # Relacionamentos
    medicos = relationship("Medico", back_populates="cliente", cascade="all, delete-orphan")
    pacientes = relationship("Paciente", back_populates="cliente", cascade="all, delete-orphan")
    configuracao = relationship("Configuracao", back_populates="cliente", uselist=False, cascade="all, delete-orphan")
    convenios = relationship("Convenio", back_populates="cliente", cascade="all, delete-orphan")
    conversas = relationship("Conversa", back_populates="cliente", cascade="all, delete-orphan")
    aceites = relationship("HistoricoAceite", back_populates="cliente", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Cliente(nome='{self.nome}', plano='{self.plano}', status='{self.status}')>"
