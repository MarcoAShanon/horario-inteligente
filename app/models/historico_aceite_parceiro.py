"""
Model para Historico de Aceites de Termos de Parceiros
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.base import Base


class HistoricoAceiteParceiro(Base):
    """Registro de aceites de termos de parceria comercial"""
    __tablename__ = 'historico_aceites_parceiros'

    id = Column(Integer, primary_key=True, autoincrement=True)
    parceiro_id = Column(Integer, ForeignKey('parceiros_comerciais.id', ondelete='CASCADE'), nullable=False, index=True)
    tipo_aceite = Column(String(50), nullable=False)  # 'ativacao_conta', 'atualizacao_termo'
    versao_termo = Column(String(20), nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    aceito_em = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    ativo = Column(Boolean, server_default='true', nullable=False)

    # Relacionamento
    parceiro = relationship("ParceiroComercial", back_populates="aceites_termo")

    def __repr__(self):
        return f"<HistoricoAceiteParceiro(parceiro_id={self.parceiro_id}, tipo='{self.tipo_aceite}', em={self.aceito_em})>"
