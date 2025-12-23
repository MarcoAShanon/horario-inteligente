"""Create despesas table

Revision ID: h06_create_despesas
Revises: h05_create_log_auditoria
Create Date: 2025-12-22

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'h06_create_despesas'
down_revision = 'h05_auditoria'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'despesas',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('descricao', sa.String(200), nullable=False),
        sa.Column('categoria', sa.String(50), nullable=False),  # 'fixa' ou 'variavel'
        sa.Column('tipo', sa.String(100), nullable=True),  # Ex: 'Infraestrutura', 'Marketing', 'Pessoal', etc.
        sa.Column('valor', sa.Numeric(10, 2), nullable=False),
        sa.Column('data_vencimento', sa.Date(), nullable=True),
        sa.Column('data_pagamento', sa.Date(), nullable=True),
        sa.Column('recorrente', sa.Boolean(), default=False),
        sa.Column('dia_recorrencia', sa.Integer(), nullable=True),  # Dia do mês para despesas recorrentes
        sa.Column('status', sa.String(20), default='pendente'),  # 'pendente', 'pago', 'cancelado'
        sa.Column('observacoes', sa.Text(), nullable=True),
        sa.Column('comprovante_url', sa.String(500), nullable=True),
        sa.Column('criado_em', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('atualizado_em', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('criado_por', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # Criar índices para buscas frequentes
    op.create_index('idx_despesas_categoria', 'despesas', ['categoria'])
    op.create_index('idx_despesas_status', 'despesas', ['status'])
    op.create_index('idx_despesas_data_vencimento', 'despesas', ['data_vencimento'])


def downgrade():
    op.drop_index('idx_despesas_data_vencimento')
    op.drop_index('idx_despesas_status')
    op.drop_index('idx_despesas_categoria')
    op.drop_table('despesas')
