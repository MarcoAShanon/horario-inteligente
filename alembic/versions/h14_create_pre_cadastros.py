"""Create pre_cadastros table for launch leads

Revision ID: h14_create_pre_cadastros
Revises: h13_create_page_views
Create Date: 2026-01-08

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'h14_create_pre_cadastros'
down_revision = 'h13_create_page_views'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'pre_cadastros',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),

        # Dados pessoais
        sa.Column('nome', sa.String(255), nullable=False),
        sa.Column('email', sa.String(255), nullable=False, unique=True),
        sa.Column('whatsapp', sa.String(20), nullable=False),

        # Dados profissionais
        sa.Column('profissao', sa.String(100), nullable=False),
        sa.Column('cidade_estado', sa.String(255), nullable=False),

        # Sistema atual
        sa.Column('usa_sistema', sa.String(255), nullable=True),
        sa.Column('nome_sistema_atual', sa.String(255), nullable=True),

        # Marketing
        sa.Column('origem', sa.String(100), nullable=True),

        # Consentimento
        sa.Column('aceite_comunicacao', sa.Boolean(), default=True, nullable=False),

        # Metadados
        sa.Column('data_cadastro', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('status', sa.String(50), default='pendente', nullable=False),
        sa.Column('ip_origem', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),

        # Timestamps padrão
        sa.Column('criado_em', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('atualizado_em', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # Índices para consultas frequentes
    op.create_index('ix_pre_cadastros_email', 'pre_cadastros', ['email'])
    op.create_index('ix_pre_cadastros_data_cadastro', 'pre_cadastros', ['data_cadastro'])
    op.create_index('ix_pre_cadastros_profissao', 'pre_cadastros', ['profissao'])
    op.create_index('ix_pre_cadastros_origem', 'pre_cadastros', ['origem'])
    op.create_index('ix_pre_cadastros_status', 'pre_cadastros', ['status'])


def downgrade():
    op.drop_index('ix_pre_cadastros_status', table_name='pre_cadastros')
    op.drop_index('ix_pre_cadastros_origem', table_name='pre_cadastros')
    op.drop_index('ix_pre_cadastros_profissao', table_name='pre_cadastros')
    op.drop_index('ix_pre_cadastros_data_cadastro', table_name='pre_cadastros')
    op.drop_index('ix_pre_cadastros_email', table_name='pre_cadastros')
    op.drop_table('pre_cadastros')
