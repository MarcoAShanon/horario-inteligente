"""
Modelo de Pagamento
Representa os pagamentos (cobranças) do ASAAS
"""
from sqlalchemy import Column, Integer, String, Text, Numeric, Date, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class Pagamento(Base):
    __tablename__ = "pagamentos"

    id = Column(Integer, primary_key=True, index=True)

    # Relacionamentos
    assinatura_id = Column(Integer, ForeignKey('assinaturas.id'), nullable=True)
    cliente_id = Column(Integer, ForeignKey('clientes.id'), nullable=False)

    # IDs ASAAS
    asaas_payment_id = Column(String(50), unique=True, index=True)  # ID do pagamento no ASAAS
    asaas_invoice_url = Column(String(500))  # URL da fatura

    # Valores
    valor = Column(Numeric(10, 2), nullable=False)
    valor_pago = Column(Numeric(10, 2))

    # Datas
    data_vencimento = Column(Date, nullable=False)
    data_pagamento = Column(Date)

    # Forma de pagamento
    forma_pagamento = Column(String(20))  # BOLETO, PIX, CREDIT_CARD

    # Links de pagamento
    link_boleto = Column(String(500))
    link_pix = Column(String(500))
    pix_copia_cola = Column(Text)

    # Status do pagamento
    # PENDING, CONFIRMED, RECEIVED, OVERDUE, REFUNDED, DELETED
    status = Column(String(20), default="PENDING")

    # Descrição e tipo
    descricao = Column(String(255))
    tipo = Column(String(20))  # ASSINATURA, ATIVACAO, AVULSO

    # Auditoria
    criado_em = Column(DateTime, server_default=func.now())
    atualizado_em = Column(DateTime, onupdate=func.now())

    # Relacionamentos
    cliente = relationship("Cliente", backref="pagamentos")
    assinatura = relationship("Assinatura", backref="pagamentos")

    def __repr__(self):
        return f"<Pagamento id={self.id} asaas_id={self.asaas_payment_id} status={self.status}>"
