"""Add periodicidade to despesas

Revision ID: h07_add_periodicidade_despesas
Revises: h06_create_despesas
Create Date: 2025-12-22

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'h07_add_periodicidade_despesas'
down_revision = 'h06_create_despesas'
branch_labels = None
depends_on = None


def upgrade():
    # Adicionar coluna periodicidade (mensal ou anual)
    op.add_column('despesas', sa.Column('periodicidade', sa.String(20), nullable=True, server_default='mensal'))


def downgrade():
    op.drop_column('despesas', 'periodicidade')
