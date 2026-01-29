"""add is_demo field to clientes

Revision ID: k04_add_is_demo_clientes
Revises: k03_comiss_parceiro_cli
Create Date: 2026-01-29

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'k04_add_is_demo_clientes'
down_revision: Union[str, None] = 'k03_comiss_parceiro_cli'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    # Adicionar coluna is_demo se não existir
    result = conn.execute(sa.text(
        "SELECT EXISTS (SELECT FROM information_schema.columns "
        "WHERE table_name = 'clientes' AND column_name = 'is_demo')"
    ))
    if not result.scalar():
        op.add_column('clientes', sa.Column(
            'is_demo', sa.Boolean(), server_default='false', nullable=False
        ))

    # Criar índice
    result = conn.execute(sa.text(
        "SELECT EXISTS (SELECT FROM pg_indexes "
        "WHERE indexname = 'idx_clientes_is_demo')"
    ))
    if not result.scalar():
        op.create_index('idx_clientes_is_demo', 'clientes', ['is_demo'])

    # Marcar cliente demo existente
    conn.execute(sa.text(
        "UPDATE clientes SET is_demo = true WHERE subdomain = 'demo'"
    ))


def downgrade() -> None:
    op.drop_index('idx_clientes_is_demo', table_name='clientes')
    op.drop_column('clientes', 'is_demo')
