"""Add email verification fields to medicos and usuarios

Revision ID: g01_email_verify
Revises: f42012c09a90
Create Date: 2025-12-21

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'g01_email_verify'
down_revision: Union[str, None] = 'f42012c09a90'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Adicionar campos na tabela medicos
    op.add_column('medicos', sa.Column('email_verificado', sa.Boolean(), nullable=True, server_default='false'))
    op.add_column('medicos', sa.Column('token_verificacao', sa.String(255), nullable=True))
    op.add_column('medicos', sa.Column('token_verificacao_expira', sa.DateTime(timezone=True), nullable=True))

    # Adicionar campos na tabela usuarios
    op.add_column('usuarios', sa.Column('email_verificado', sa.Boolean(), nullable=True, server_default='false'))
    op.add_column('usuarios', sa.Column('token_verificacao', sa.String(255), nullable=True))
    op.add_column('usuarios', sa.Column('token_verificacao_expira', sa.DateTime(timezone=True), nullable=True))

    # Marcar usuários existentes como já verificados (não quebrar contas existentes)
    op.execute("UPDATE medicos SET email_verificado = true WHERE email_verificado IS NULL")
    op.execute("UPDATE usuarios SET email_verificado = true WHERE email_verificado IS NULL")


def downgrade() -> None:
    # Remover campos da tabela medicos
    op.drop_column('medicos', 'email_verificado')
    op.drop_column('medicos', 'token_verificacao')
    op.drop_column('medicos', 'token_verificacao_expira')

    # Remover campos da tabela usuarios
    op.drop_column('usuarios', 'email_verificado')
    op.drop_column('usuarios', 'token_verificacao')
    op.drop_column('usuarios', 'token_verificacao_expira')
