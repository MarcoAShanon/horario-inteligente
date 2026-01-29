"""add auth fields to parceiros_comerciais

Revision ID: j03_parceiro_auth
Revises: j02_historico_aceites
Create Date: 2026-01-28

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'j03_parceiro_auth'
down_revision: Union[str, None] = 'j02_historico_aceites'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('parceiros_comerciais',
        sa.Column('senha_hash', sa.String(255), nullable=True)
    )
    op.add_column('parceiros_comerciais',
        sa.Column('token_login', sa.String(255), nullable=True)
    )
    op.add_column('parceiros_comerciais',
        sa.Column('ultimo_login', sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('parceiros_comerciais', 'ultimo_login')
    op.drop_column('parceiros_comerciais', 'token_login')
    op.drop_column('parceiros_comerciais', 'senha_hash')
