"""create comissionamento_parceiro_cliente table

Revision ID: k03_comiss_parceiro_cli
Revises: k02_hist_aceites_parceiro
Create Date: 2026-01-29

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'k03_comiss_parceiro_cli'
down_revision: Union[str, None] = 'k02_hist_aceites_parceiro'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    # Verificar se tabela já existe
    result = conn.execute(sa.text(
        "SELECT EXISTS (SELECT FROM information_schema.tables "
        "WHERE table_name = 'comissionamento_parceiro_cliente')"
    ))
    if result.scalar():
        return

    op.create_table(
        'comissionamento_parceiro_cliente',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('parceiro_id', sa.Integer(), sa.ForeignKey('parceiros_comerciais.id'), nullable=False),
        sa.Column('cliente_id', sa.Integer(), sa.ForeignKey('clientes.id'), nullable=False),
        sa.Column('data_inicio', sa.Date(), nullable=False),
        sa.Column('data_fim', sa.Date(), nullable=True),
        sa.Column('renovado', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('data_renovacao', sa.Date(), nullable=True),
        sa.Column('observacoes', sa.Text(), nullable=True),
        sa.Column('ativo', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('criado_em', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_index('idx_comiss_parceiro', 'comissionamento_parceiro_cliente', ['parceiro_id'])
    op.create_index('idx_comiss_cliente', 'comissionamento_parceiro_cliente', ['cliente_id'])


def downgrade() -> None:
    op.drop_index('idx_comiss_cliente', table_name='comissionamento_parceiro_cliente')
    op.drop_index('idx_comiss_parceiro', table_name='comissionamento_parceiro_cliente')
    op.drop_table('comissionamento_parceiro_cliente')
