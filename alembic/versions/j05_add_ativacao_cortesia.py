"""add ativacao_cortesia to assinaturas

Revision ID: j05_ativacao_cortesia
Revises: j04_historico_inadimplencia
Create Date: 2026-01-28

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'j05_ativacao_cortesia'
down_revision: Union[str, None] = 'j04_historico_inadimplencia'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    # Adicionar coluna ativacao_cortesia se não existir
    result = conn.execute(sa.text(
        "SELECT EXISTS (SELECT FROM information_schema.columns "
        "WHERE table_name = 'assinaturas' AND column_name = 'ativacao_cortesia')"
    ))
    if not result.scalar():
        op.add_column('assinaturas', sa.Column('ativacao_cortesia', sa.Boolean, server_default='false', nullable=False))


def downgrade() -> None:
    op.drop_column('assinaturas', 'ativacao_cortesia')
