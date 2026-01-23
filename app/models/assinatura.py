"""
Modelo de Assinatura
Representa o vínculo entre um cliente e um plano
"""
from sqlalchemy import Column, Integer, String, Text, Numeric, Boolean, DateTime, Date, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base
from decimal import Decimal


class Assinatura(Base):
    __tablename__ = "assinaturas"

    id = Column(Integer, primary_key=True, index=True)
    cliente_id = Column(Integer, ForeignKey('clientes.id'), nullable=False)
    plano_id = Column(Integer, ForeignKey('planos.id'), nullable=False)

    # Valores
    valor_mensal = Column(Numeric(10, 2), nullable=False)
    valor_profissional_adicional = Column(Numeric(10, 2), default=50.00)
    profissionais_contratados = Column(Integer, default=1)

    # Taxa de ativação
    taxa_ativacao = Column(Numeric(10, 2), default=150.00)
    taxa_ativacao_paga = Column(Boolean, default=False)
    desconto_ativacao_percentual = Column(Numeric(5, 2), default=0)
    motivo_desconto_ativacao = Column(String(100))

    # Serviços adicionais
    numero_virtual_salvy = Column(Boolean, default=False)
    valor_numero_virtual = Column(Numeric(10, 2), default=40.00)

    # Datas
    data_inicio = Column(Date, nullable=False)
    data_fim = Column(Date)  # NULL = ativa
    dia_vencimento = Column(Integer, default=10)

    # Status
    status = Column(String(20), default='ativa')  # ativa, suspensa, cancelada
    motivo_cancelamento = Column(Text)

    # ASAAS Integration
    asaas_subscription_id = Column(String(50), nullable=True, index=True)  # ID da assinatura no ASAAS

    # Auditoria
    criado_em = Column(DateTime, server_default=func.now())
    atualizado_em = Column(DateTime, onupdate=func.now())

    # Relacionamentos - usar lazy='select' para evitar problemas de carregamento circular
    plano = relationship("Plano", back_populates="assinaturas", lazy="select")

    @property
    def valor_total_mensal(self) -> Decimal:
        """Calcula valor total mensal incluindo adicionais"""
        base = self.valor_mensal or Decimal('0')

        # Profissionais além do incluso no plano
        if self.plano:
            adicionais = max(0, (self.profissionais_contratados or 1) - (self.plano.profissionais_inclusos or 1))
            base += adicionais * (self.valor_profissional_adicional or Decimal('50.00'))

        # Número virtual
        if self.numero_virtual_salvy:
            base += self.valor_numero_virtual or Decimal('40.00')

        return base

    @property
    def taxa_ativacao_final(self) -> Decimal:
        """Calcula taxa de ativação com desconto aplicado"""
        taxa = self.taxa_ativacao or Decimal('150.00')
        desconto_pct = self.desconto_ativacao_percentual or Decimal('0')
        desconto = taxa * (desconto_pct / 100)
        return taxa - desconto

    @property
    def is_ativa(self) -> bool:
        return self.status == 'ativa' and self.data_fim is None

    def __repr__(self):
        return f"<Assinatura cliente_id={self.cliente_id} plano={self.plano_id} status={self.status}>"
