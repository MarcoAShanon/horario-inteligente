"""
Model para Usuarios Internos (Admin, Financeiro, Suporte)
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from app.models.base import Base


class UsuarioInterno(Base):
    """Usuarios internos do sistema (equipe Horário Inteligente)"""
    __tablename__ = 'usuarios_internos'

    id = Column(Integer, primary_key=True, autoincrement=True)
    nome = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, unique=True)
    senha_hash = Column(String(255), nullable=False)
    perfil = Column(String(50), nullable=False)  # 'admin', 'financeiro', 'suporte'
    telefone = Column(String(20), nullable=True)
    ativo = Column(Boolean, default=True)
    ultimo_acesso = Column(DateTime(timezone=True), nullable=True)
    criado_em = Column(DateTime(timezone=True), server_default=func.now())
    atualizado_em = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Perfis disponíveis
    PERFIL_ADMIN = 'admin'
    PERFIL_FINANCEIRO = 'financeiro'
    PERFIL_SUPORTE = 'suporte'

    PERFIS_VALIDOS = [PERFIL_ADMIN, PERFIL_FINANCEIRO, PERFIL_SUPORTE]

    def to_dict(self):
        """Converte para dicionário (sem senha)"""
        return {
            'id': self.id,
            'nome': self.nome,
            'email': self.email,
            'perfil': self.perfil,
            'telefone': self.telefone,
            'ativo': self.ativo,
            'ultimo_acesso': self.ultimo_acesso.isoformat() if self.ultimo_acesso else None,
            'criado_em': self.criado_em.isoformat() if self.criado_em else None,
            'atualizado_em': self.atualizado_em.isoformat() if self.atualizado_em else None
        }

    def __repr__(self):
        return f"<UsuarioInterno(id={self.id}, email='{self.email}', perfil='{self.perfil}')>"
