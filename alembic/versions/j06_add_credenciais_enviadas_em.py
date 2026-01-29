"""add credenciais_enviadas_em to clientes

Revision ID: j06_add_credenciais_enviadas_em
Revises: j05_ativacao_cortesia
Create Date: 2026-01-28

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'j06_add_credenciais_enviadas_em'
down_revision: Union[str, None] = 'j05_ativacao_cortesia'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    # Adicionar coluna credenciais_enviadas_em se não existir
    result = conn.execute(sa.text(
        "SELECT EXISTS (SELECT FROM information_schema.columns "
        "WHERE table_name = 'clientes' AND column_name = 'credenciais_enviadas_em')"
    ))
    if not result.scalar():
        op.add_column('clientes', sa.Column('credenciais_enviadas_em', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('clientes', 'credenciais_enviadas_em')
