"""
Integração ASAAS - Adiciona campos e tabela de pagamentos

Revision ID: h15_asaas_integration
Revises: h14_create_pre_cadastros
Create Date: 2026-01-21
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'h15_asaas_integration'
down_revision = '2e94e08eeb1d'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Adicionar campo asaas_customer_id na tabela clientes
    op.add_column('clientes', sa.Column('asaas_customer_id', sa.String(50), nullable=True))
    op.create_index('ix_clientes_asaas_customer_id', 'clientes', ['asaas_customer_id'])

    # 2. Adicionar campo asaas_subscription_id na tabela assinaturas
    op.add_column('assinaturas', sa.Column('asaas_subscription_id', sa.String(50), nullable=True))
    op.create_index('ix_assinaturas_asaas_subscription_id', 'assinaturas', ['asaas_subscription_id'])

    # 3. Criar tabela pagamentos
    op.create_table(
        'pagamentos',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('assinatura_id', sa.Integer(), sa.ForeignKey('assinaturas.id'), nullable=True),
        sa.Column('cliente_id', sa.Integer(), sa.ForeignKey('clientes.id'), nullable=False),

        # IDs ASAAS
        sa.Column('asaas_payment_id', sa.String(50), unique=True, index=True),
        sa.Column('asaas_invoice_url', sa.String(500)),

        # Valores
        sa.Column('valor', sa.Numeric(10, 2), nullable=False),
        sa.Column('valor_pago', sa.Numeric(10, 2)),

        # Datas
        sa.Column('data_vencimento', sa.Date(), nullable=False),
        sa.Column('data_pagamento', sa.Date()),

        # Forma de pagamento
        sa.Column('forma_pagamento', sa.String(20)),  # BOLETO, PIX, CREDIT_CARD

        # Links de pagamento
        sa.Column('link_boleto', sa.String(500)),
        sa.Column('link_pix', sa.String(500)),
        sa.Column('pix_copia_cola', sa.Text()),

        # Status
        sa.Column('status', sa.String(20), server_default="'PENDING'"),

        # Descrição e tipo
        sa.Column('descricao', sa.String(255)),
        sa.Column('tipo', sa.String(20)),  # ASSINATURA, ATIVACAO, AVULSO

        # Auditoria
        sa.Column('criado_em', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('atualizado_em', sa.DateTime(), onupdate=sa.func.now())
    )

    op.create_index('ix_pagamentos_cliente_id', 'pagamentos', ['cliente_id'])
    op.create_index('ix_pagamentos_assinatura_id', 'pagamentos', ['assinatura_id'])
    op.create_index('ix_pagamentos_status', 'pagamentos', ['status'])
    op.create_index('ix_pagamentos_data_vencimento', 'pagamentos', ['data_vencimento'])


def downgrade():
    # Remover tabela pagamentos
    op.drop_index('ix_pagamentos_data_vencimento')
    op.drop_index('ix_pagamentos_status')
    op.drop_index('ix_pagamentos_assinatura_id')
    op.drop_index('ix_pagamentos_cliente_id')
    op.drop_table('pagamentos')

    # Remover campo asaas_subscription_id da tabela assinaturas
    op.drop_index('ix_assinaturas_asaas_subscription_id')
    op.drop_column('assinaturas', 'asaas_subscription_id')

    # Remover campo asaas_customer_id da tabela clientes
    op.drop_index('ix_clientes_asaas_customer_id')
    op.drop_column('clientes', 'asaas_customer_id')
