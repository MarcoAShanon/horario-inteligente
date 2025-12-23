"""create historico agendamentos table

Revision ID: b56a107318a5
Revises: e285ad2965fa
Create Date: 2025-11-28 12:53:02.589671

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b56a107318a5'
down_revision: Union[str, Sequence[str], None] = 'e285ad2965fa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Criar tabela de histórico de agendamentos
    op.create_table(
        'historico_agendamentos',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('agendamento_id', sa.Integer(), nullable=False),
        sa.Column('acao', sa.String(length=50), nullable=False),
        sa.Column('descricao', sa.Text(), nullable=True),
        sa.Column('criado_em', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['agendamento_id'], ['agendamentos.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Criar índice para otimizar consultas
    op.create_index(
        'ix_historico_agendamentos_agendamento_id',
        'historico_agendamentos',
        ['agendamento_id']
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_historico_agendamentos_agendamento_id')
    op.drop_table('historico_agendamentos')
