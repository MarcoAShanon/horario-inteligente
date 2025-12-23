"""adicionar_campos_branding_cliente_v2

Revision ID: 6a4861dcd18b
Revises: 6bb8e2ca6b09
Create Date: 2025-12-02 11:29:26.042746

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6a4861dcd18b'
down_revision: Union[str, Sequence[str], None] = '6bb8e2ca6b09'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Adiciona campos de branding ao modelo Cliente."""
    # Adicionar colunas como nullable primeiro
    op.add_column('clientes', sa.Column('logo_url', sa.String(length=500), nullable=True))
    op.add_column('clientes', sa.Column('logo_icon', sa.String(length=100), nullable=True))
    op.add_column('clientes', sa.Column('cor_primaria', sa.String(length=7), nullable=True))
    op.add_column('clientes', sa.Column('cor_secundaria', sa.String(length=7), nullable=True))
    op.add_column('clientes', sa.Column('favicon_url', sa.String(length=500), nullable=True))

    # Atualizar registros existentes com valores padrão
    op.execute("UPDATE clientes SET logo_icon = 'fa-heartbeat' WHERE logo_icon IS NULL")
    op.execute("UPDATE clientes SET cor_primaria = '#3b82f6' WHERE cor_primaria IS NULL")
    op.execute("UPDATE clientes SET cor_secundaria = '#1e40af' WHERE cor_secundaria IS NULL")

    # Alterar colunas para NOT NULL (exceto as opcionais logo_url e favicon_url)
    op.alter_column('clientes', 'logo_icon', nullable=False)
    op.alter_column('clientes', 'cor_primaria', nullable=False)
    op.alter_column('clientes', 'cor_secundaria', nullable=False)


def downgrade() -> None:
    """Remove campos de branding do modelo Cliente."""
    op.drop_column('clientes', 'favicon_url')
    op.drop_column('clientes', 'cor_secundaria')
    op.drop_column('clientes', 'cor_primaria')
    op.drop_column('clientes', 'logo_icon')
    op.drop_column('clientes', 'logo_url')
