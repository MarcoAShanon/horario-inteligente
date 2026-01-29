"""create historico_aceites table

Revision ID: j02_historico_aceites
Revises: j01_onboarding_fields
Create Date: 2026-01-28

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'j02_historico_aceites'
down_revision: Union[str, None] = 'j01_onboarding_fields'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'historico_aceites',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('cliente_id', sa.Integer(), sa.ForeignKey('clientes.id', ondelete='CASCADE'), nullable=False),
        sa.Column('tipo_aceite', sa.String(50), nullable=False),  # 'ativacao', 'atualizacao_termos'
        sa.Column('versao_termos', sa.String(10), nullable=True),
        sa.Column('versao_privacidade', sa.String(10), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('aceito_em', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('ativo', sa.Boolean(), server_default='true', nullable=False),
    )

    op.create_index('ix_historico_aceites_cliente_id', 'historico_aceites', ['cliente_id'])


def downgrade() -> None:
    op.drop_index('ix_historico_aceites_cliente_id', table_name='historico_aceites')
    op.drop_table('historico_aceites')
