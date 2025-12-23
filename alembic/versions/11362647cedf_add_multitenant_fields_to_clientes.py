"""add_multitenant_fields_to_clientes

Revision ID: 11362647cedf
Revises: 97b9341b7318
Create Date: 2025-11-30 14:02:29.250344

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '11362647cedf'
down_revision: Union[str, Sequence[str], None] = '97b9341b7318'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Adicionar campos para multi-tenant
    op.add_column('clientes', sa.Column('subdomain', sa.String(100), nullable=True, unique=True))
    op.add_column('clientes', sa.Column('whatsapp_instance', sa.String(100), nullable=True))
    op.add_column('clientes', sa.Column('whatsapp_numero', sa.String(20), nullable=True))

    # Atualizar cliente existente (Pro-Saúde) com subdomínio padrão
    op.execute("UPDATE clientes SET subdomain = 'prosaude', whatsapp_instance = 'ProSaude' WHERE id = 1")

    # Criar índice para busca rápida por subdomínio
    op.create_index('idx_clientes_subdomain', 'clientes', ['subdomain'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('idx_clientes_subdomain', table_name='clientes')
    op.drop_column('clientes', 'whatsapp_numero')
    op.drop_column('clientes', 'whatsapp_instance')
    op.drop_column('clientes', 'subdomain')
