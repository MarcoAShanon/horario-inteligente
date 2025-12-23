"""add reminder fields to agendamento

Revision ID: e285ad2965fa
Revises: 178cfa2f4702
Create Date: 2025-11-28 12:37:00.825766

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e285ad2965fa'
down_revision: Union[str, Sequence[str], None] = '178cfa2f4702'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Adicionar novos campos de controle de lembretes
    op.add_column('agendamentos', sa.Column('lembrete_3h_enviado', sa.Boolean(), nullable=True, default=False))
    op.add_column('agendamentos', sa.Column('lembrete_1h_enviado', sa.Boolean(), nullable=True, default=False))

    # Atualizar valores existentes para False
    op.execute("UPDATE agendamentos SET lembrete_3h_enviado = false WHERE lembrete_3h_enviado IS NULL")
    op.execute("UPDATE agendamentos SET lembrete_1h_enviado = false WHERE lembrete_1h_enviado IS NULL")


def downgrade() -> None:
    """Downgrade schema."""
    # Remover campos de lembretes
    op.drop_column('agendamentos', 'lembrete_1h_enviado')
    op.drop_column('agendamentos', 'lembrete_3h_enviado')
