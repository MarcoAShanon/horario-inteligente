"""add senha field to medicos

Revision ID: 97b9341b7318
Revises: b56a107318a5
Create Date: 2025-11-28 12:56:43.234126

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '97b9341b7318'
down_revision: Union[str, Sequence[str], None] = 'b56a107318a5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Adicionar campo senha na tabela medicos
    op.add_column('medicos', sa.Column('senha', sa.String(length=255), nullable=True))

    # Definir senha padrão para médicos existentes (desenvolvimento)
    op.execute("UPDATE medicos SET senha = 'admin123' WHERE senha IS NULL")

    # Criar tabela de usuários (secretárias, admins)
    op.create_table(
        'usuarios',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('nome', sa.String(length=200), nullable=False),
        sa.Column('email', sa.String(length=200), nullable=False),
        sa.Column('senha', sa.String(length=255), nullable=False),
        sa.Column('tipo', sa.String(length=50), nullable=False, server_default='secretaria'),
        sa.Column('telefone', sa.String(length=20), nullable=True),
        sa.Column('ativo', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('cliente_id', sa.Integer(), nullable=False),
        sa.Column('criado_em', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('atualizado_em', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['cliente_id'], ['clientes.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )

    # Criar índice
    op.create_index('ix_usuarios_email', 'usuarios', ['email'])

    # Inserir usuário admin padrão
    op.execute("""
        INSERT INTO usuarios (nome, email, senha, tipo, ativo, cliente_id)
        VALUES ('Administrador', 'admin@prosaude.com', 'admin123', 'secretaria', true, 1)
    """)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_usuarios_email')
    op.drop_table('usuarios')
    op.drop_column('medicos', 'senha')
