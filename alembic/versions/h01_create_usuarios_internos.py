"""Create usuarios_internos table

Revision ID: h01_usuarios_int
Revises: g01_email_verify
Create Date: 2025-12-21

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'h01_usuarios_int'
down_revision: Union[str, None] = 'g01_email_verify'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'usuarios_internos',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('nome', sa.String(255), nullable=False),
        sa.Column('email', sa.String(255), nullable=False, unique=True),
        sa.Column('senha_hash', sa.String(255), nullable=False),
        sa.Column('perfil', sa.String(50), nullable=False),  # 'admin', 'financeiro', 'suporte'
        sa.Column('telefone', sa.String(20), nullable=True),
        sa.Column('ativo', sa.Boolean(), server_default='true'),
        sa.Column('ultimo_acesso', sa.DateTime(timezone=True), nullable=True),
        sa.Column('criado_em', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('atualizado_em', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Índice para busca por email
    op.create_index('ix_usuarios_internos_email', 'usuarios_internos', ['email'])

    # Índice para busca por perfil
    op.create_index('ix_usuarios_internos_perfil', 'usuarios_internos', ['perfil'])


def downgrade() -> None:
    op.drop_index('ix_usuarios_internos_perfil', table_name='usuarios_internos')
    op.drop_index('ix_usuarios_internos_email', table_name='usuarios_internos')
    op.drop_table('usuarios_internos')
