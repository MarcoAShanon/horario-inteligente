"""add codigo_ativacao to parceiros_comerciais

Revision ID: k06_add_codigo_ativacao
Revises: k05_whatsapp_msg_log
Create Date: 2026-01-29

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'k06_add_codigo_ativacao'
down_revision: Union[str, None] = 'k05_whatsapp_msg_log'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    # Verificar se coluna ja existe
    result = conn.execute(sa.text(
        "SELECT EXISTS (SELECT FROM information_schema.columns "
        "WHERE table_name = 'parceiros_comerciais' AND column_name = 'codigo_ativacao')"
    ))
    if not result.scalar():
        op.add_column('parceiros_comerciais',
            sa.Column('codigo_ativacao', sa.String(12), nullable=True)
        )
        op.create_unique_constraint(
            'uq_parceiros_codigo_ativacao',
            'parceiros_comerciais',
            ['codigo_ativacao']
        )


def downgrade() -> None:
    op.drop_constraint('uq_parceiros_codigo_ativacao', 'parceiros_comerciais', type_='unique')
    op.drop_column('parceiros_comerciais', 'codigo_ativacao')
