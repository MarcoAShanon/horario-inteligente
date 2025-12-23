"""Create clientes_parceiros table

Revision ID: h03_cli_parceiros
Revises: h02_parceiros
Create Date: 2025-12-21

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'h03_cli_parceiros'
down_revision: Union[str, None] = 'h02_parceiros'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'clientes_parceiros',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('cliente_id', sa.Integer(), sa.ForeignKey('clientes.id', ondelete='CASCADE'), nullable=False),
        sa.Column('parceiro_id', sa.Integer(), sa.ForeignKey('parceiros_comerciais.id', ondelete='CASCADE'), nullable=False),

        # Data do vínculo
        sa.Column('data_vinculo', sa.Date(), nullable=False),
        sa.Column('data_desvinculo', sa.Date(), nullable=True),

        # Override de comissão para este cliente específico (opcional)
        sa.Column('percentual_comissao_override', sa.Numeric(5, 2), nullable=True),

        # Observações
        sa.Column('observacoes', sa.Text(), nullable=True),

        # Status
        sa.Column('ativo', sa.Boolean(), server_default='true'),
        sa.Column('criado_em', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('atualizado_em', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Constraint única: um cliente só pode estar vinculado a um parceiro uma vez (ativo)
    op.create_unique_constraint(
        'uq_cliente_parceiro_ativo',
        'clientes_parceiros',
        ['cliente_id', 'parceiro_id']
    )

    # Índices para buscas
    op.create_index('ix_clientes_parceiros_cliente', 'clientes_parceiros', ['cliente_id'])
    op.create_index('ix_clientes_parceiros_parceiro', 'clientes_parceiros', ['parceiro_id'])
    op.create_index('ix_clientes_parceiros_ativo', 'clientes_parceiros', ['ativo'])


def downgrade() -> None:
    op.drop_index('ix_clientes_parceiros_ativo', table_name='clientes_parceiros')
    op.drop_index('ix_clientes_parceiros_parceiro', table_name='clientes_parceiros')
    op.drop_index('ix_clientes_parceiros_cliente', table_name='clientes_parceiros')
    op.drop_constraint('uq_cliente_parceiro_ativo', 'clientes_parceiros', type_='unique')
    op.drop_table('clientes_parceiros')
