"""
Model para Convites de Registro de Clientes (Self-Service)
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.sql import func
from app.models.base import Base


class ConviteCliente(Base):
    """Convites personalizados para registro de clientes"""
    __tablename__ = 'convites_clientes'

    id = Column(Integer, primary_key=True, autoincrement=True)
    token = Column(String(100), nullable=False, unique=True, index=True)
    email_destino = Column(String(255), nullable=True)
    nome_destino = Column(String(255), nullable=True)
    telefone_destino = Column(String(20), nullable=True)
    observacoes = Column(Text, nullable=True)
    criado_por_id = Column(Integer, nullable=False)
    criado_por_tipo = Column(String(20), server_default='admin')
    parceiro_id = Column(Integer, nullable=True)
    usado = Column(Boolean, server_default='false')
    usado_em = Column(DateTime(timezone=True), nullable=True)
    cliente_id = Column(Integer, nullable=True)
    expira_em = Column(DateTime(timezone=True), nullable=False)
    criado_em = Column(DateTime(timezone=True), server_default=func.now())

    def to_dict(self):
        """Converte para dicionario"""
        from datetime import datetime, timezone
        agora = datetime.now(timezone.utc)
        expirado = self.expira_em < agora if self.expira_em else False

        if self.usado:
            status = 'usado'
        elif expirado:
            status = 'expirado'
        else:
            status = 'pendente'

        return {
            'id': self.id,
            'token': self.token,
            'email_destino': self.email_destino,
            'nome_destino': self.nome_destino,
            'telefone_destino': self.telefone_destino,
            'observacoes': self.observacoes,
            'criado_por_id': self.criado_por_id,
            'criado_por_tipo': self.criado_por_tipo,
            'parceiro_id': self.parceiro_id,
            'usado': self.usado,
            'usado_em': self.usado_em.isoformat() if self.usado_em else None,
            'cliente_id': self.cliente_id,
            'expira_em': self.expira_em.isoformat() if self.expira_em else None,
            'criado_em': self.criado_em.isoformat() if self.criado_em else None,
            'status': status,
        }

    def __repr__(self):
        return f"<ConviteCliente(id={self.id}, token='{self.token[:8]}...', usado={self.usado})>"
