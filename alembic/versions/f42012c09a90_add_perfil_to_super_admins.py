"""add_perfil_to_super_admins

Revision ID: f42012c09a90
Revises: 6a4861dcd18b
Create Date: 2025-12-03 22:01:06.188286

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f42012c09a90'
down_revision: Union[str, Sequence[str], None] = '6a4861dcd18b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Adicionar coluna perfil na tabela super_admins
    # Valores possíveis: 'super_admin' (gestão técnica) ou 'financeiro' (gestão financeira)
    op.add_column('super_admins', sa.Column('perfil', sa.String(20), nullable=False, server_default='super_admin'))

    # Criar índice para otimizar consultas por perfil
    op.create_index('idx_super_admins_perfil', 'super_admins', ['perfil'])


def downgrade() -> None:
    """Downgrade schema."""
    # Remover índice
    op.drop_index('idx_super_admins_perfil', 'super_admins')

    # Remover coluna perfil
    op.drop_column('super_admins', 'perfil')
