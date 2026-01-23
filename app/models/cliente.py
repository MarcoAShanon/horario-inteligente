from sqlalchemy import Column, String, Boolean, Text
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
    subdomain = Column(String(100), unique=True, nullable=True, index=True)  # drmarco, prosaude, etc
    whatsapp_instance = Column(String(100), nullable=True)  # Nome da instância Evolution API
    whatsapp_numero = Column(String(20), nullable=True)  # Número WhatsApp da clínica

    # Branding e Identidade Visual (NOVO - v3.4.0)
    logo_url = Column(String(500), nullable=True)  # URL da logo (ex: /static/logos/prosaude.png)
    logo_icon = Column(String(100), default="fa-heartbeat", nullable=False)  # Ícone FontAwesome
    cor_primaria = Column(String(7), default="#3b82f6", nullable=False)  # Cor primária (hex)
    cor_secundaria = Column(String(7), default="#1e40af", nullable=False)  # Cor secundária (hex)
    favicon_url = Column(String(500), nullable=True)  # URL do favicon

    # Configurações do plano
    plano = Column(String(50), default="basico", nullable=False)  # basico, profissional, enterprise
    ativo = Column(Boolean, default=True, nullable=False)
    valor_mensalidade = Column(String(10), default="150.00", nullable=False)

    # ASAAS Integration
    asaas_customer_id = Column(String(50), nullable=True, index=True)  # ID do cliente no ASAAS
    
    # Relacionamentos
    medicos = relationship("Medico", back_populates="cliente", cascade="all, delete-orphan")
    pacientes = relationship("Paciente", back_populates="cliente", cascade="all, delete-orphan")
    configuracao = relationship("Configuracao", back_populates="cliente", uselist=False, cascade="all, delete-orphan")
    convenios = relationship("Convenio", back_populates="cliente", cascade="all, delete-orphan")
    conversas = relationship("Conversa", back_populates="cliente", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Cliente(nome='{self.nome}', plano='{self.plano}')>"
