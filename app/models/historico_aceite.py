"""
Model para Histórico de Aceites de Termos
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.base import Base


class HistoricoAceite(Base):
    """Registro de aceites de termos de uso e privacidade"""
    __tablename__ = 'historico_aceites'

    id = Column(Integer, primary_key=True, autoincrement=True)
    cliente_id = Column(Integer, ForeignKey('clientes.id', ondelete='CASCADE'), nullable=False, index=True)
    tipo_aceite = Column(String(50), nullable=False)  # 'ativacao', 'atualizacao_termos'
    versao_termos = Column(String(10), nullable=True)
    versao_privacidade = Column(String(10), nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    aceito_em = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    ativo = Column(Boolean, server_default='true', nullable=False)

    # Relacionamento
    cliente = relationship("Cliente", back_populates="aceites")

    def __repr__(self):
        return f"<HistoricoAceite(cliente_id={self.cliente_id}, tipo='{self.tipo_aceite}', em={self.aceito_em})>"
