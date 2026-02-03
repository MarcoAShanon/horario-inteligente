"""create convites_clientes table and add columns to clientes

Revision ID: l01_create_convites_clientes
Revises: k06_add_codigo_ativacao
Create Date: 2026-02-02

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'l01_create_convites_clientes'
down_revision: Union[str, None] = 'k06_add_codigo_ativacao'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    # 1. Criar tabela convites_clientes
    result = conn.execute(sa.text(
        "SELECT EXISTS (SELECT FROM information_schema.tables "
        "WHERE table_name = 'convites_clientes')"
    ))
    if not result.scalar():
        op.create_table(
            'convites_clientes',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('token', sa.String(100), nullable=False, unique=True),
            sa.Column('email_destino', sa.String(255), nullable=True),
            sa.Column('nome_destino', sa.String(255), nullable=True),
            sa.Column('telefone_destino', sa.String(20), nullable=True),
            sa.Column('observacoes', sa.Text(), nullable=True),
            sa.Column('criado_por_id', sa.Integer(), nullable=False),
            sa.Column('criado_por_tipo', sa.String(20), server_default='admin'),
            sa.Column('parceiro_id', sa.Integer(), nullable=True),
            sa.Column('usado', sa.Boolean(), server_default='false'),
            sa.Column('usado_em', sa.DateTime(timezone=True), nullable=True),
            sa.Column('cliente_id', sa.Integer(), nullable=True),
            sa.Column('expira_em', sa.DateTime(timezone=True), nullable=False),
            sa.Column('criado_em', sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index('ix_convites_token', 'convites_clientes', ['token'])

    # 2. Adicionar novas colunas em clientes
    # tipo_consultorio
    result = conn.execute(sa.text(
        "SELECT EXISTS (SELECT FROM information_schema.columns "
        "WHERE table_name = 'clientes' AND column_name = 'tipo_consultorio')"
    ))
    if not result.scalar():
        op.add_column('clientes',
            sa.Column('tipo_consultorio', sa.String(30), server_default='individual')
        )

    # qtd_medicos_adicionais
    result = conn.execute(sa.text(
        "SELECT EXISTS (SELECT FROM information_schema.columns "
        "WHERE table_name = 'clientes' AND column_name = 'qtd_medicos_adicionais')"
    ))
    if not result.scalar():
        op.add_column('clientes',
            sa.Column('qtd_medicos_adicionais', sa.Integer(), server_default='0')
        )

    # necessita_secretaria
    result = conn.execute(sa.text(
        "SELECT EXISTS (SELECT FROM information_schema.columns "
        "WHERE table_name = 'clientes' AND column_name = 'necessita_secretaria')"
    ))
    if not result.scalar():
        op.add_column('clientes',
            sa.Column('necessita_secretaria', sa.Boolean(), server_default='false')
        )

    # convite_id
    result = conn.execute(sa.text(
        "SELECT EXISTS (SELECT FROM information_schema.columns "
        "WHERE table_name = 'clientes' AND column_name = 'convite_id')"
    ))
    if not result.scalar():
        op.add_column('clientes',
            sa.Column('convite_id', sa.Integer(), nullable=True)
        )
        op.create_foreign_key(
            'fk_clientes_convite_id',
            'clientes', 'convites_clientes',
            ['convite_id'], ['id']
        )


def downgrade() -> None:
    op.drop_constraint('fk_clientes_convite_id', 'clientes', type_='foreignkey')
    op.drop_column('clientes', 'convite_id')
    op.drop_column('clientes', 'necessita_secretaria')
    op.drop_column('clientes', 'qtd_medicos_adicionais')
    op.drop_column('clientes', 'tipo_consultorio')
    op.drop_index('ix_convites_token', table_name='convites_clientes')
    op.drop_table('convites_clientes')
