"""create historico_aceites_parceiros table

Revision ID: k02_hist_aceites_parceiro
Revises: k01_parceiro_ativacao
Create Date: 2026-01-29

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'k02_hist_aceites_parceiro'
down_revision: Union[str, None] = 'k01_parceiro_ativacao'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    # Verificar se tabela já existe
    result = conn.execute(sa.text(
        "SELECT EXISTS (SELECT FROM information_schema.tables "
        "WHERE table_name = 'historico_aceites_parceiros')"
    ))
    if result.scalar():
        return

    op.create_table(
        'historico_aceites_parceiros',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('parceiro_id', sa.Integer(), sa.ForeignKey('parceiros_comerciais.id', ondelete='CASCADE'), nullable=False),
        sa.Column('tipo_aceite', sa.String(50), nullable=False),
        sa.Column('versao_termo', sa.String(20), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('aceito_em', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('ativo', sa.Boolean(), server_default='true', nullable=False),
    )

    op.create_index('idx_hist_aceites_parceiro', 'historico_aceites_parceiros', ['parceiro_id'])


def downgrade() -> None:
    op.drop_index('idx_hist_aceites_parceiro', table_name='historico_aceites_parceiros')
    op.drop_table('historico_aceites_parceiros')
