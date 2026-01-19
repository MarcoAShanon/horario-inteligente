"""add conversa and mensagem tables

Revision ID: 2e94e08eeb1d
Revises: h14_create_pre_cadastros
Create Date: 2026-01-19 14:08:01.718978

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2e94e08eeb1d'
down_revision: Union[str, Sequence[str], None] = 'h14_create_pre_cadastros'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Criar tabelas de conversas e mensagens do WhatsApp."""

    # Criar tabela de conversas
    op.create_table('conversas',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('cliente_id', sa.Integer(), nullable=False),
        sa.Column('paciente_telefone', sa.String(length=20), nullable=False),
        sa.Column('paciente_nome', sa.String(length=100), nullable=True),
        sa.Column('status', sa.Enum('IA_ATIVA', 'HUMANO_ASSUMIU', 'ENCERRADA', name='statusconversa'), nullable=False, server_default='IA_ATIVA'),
        sa.Column('atendente_id', sa.Integer(), nullable=True),
        sa.Column('ultima_mensagem_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('closed_at', sa.DateTime(), nullable=True),
        sa.Column('criado_em', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('atualizado_em', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['atendente_id'], ['medicos.id'], ),
        sa.ForeignKeyConstraint(['cliente_id'], ['clientes.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Índices para conversas
    op.create_index('ix_conversa_cliente_telefone', 'conversas', ['cliente_id', 'paciente_telefone'], unique=False)
    op.create_index(op.f('ix_conversas_paciente_telefone'), 'conversas', ['paciente_telefone'], unique=False)

    # Criar tabela de mensagens
    op.create_table('mensagens',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('conversa_id', sa.Integer(), nullable=False),
        sa.Column('direcao', sa.Enum('ENTRADA', 'SAIDA', name='direcaomensagem'), nullable=False),
        sa.Column('remetente', sa.Enum('PACIENTE', 'IA', 'ATENDENTE', name='remetentemensagem'), nullable=False),
        sa.Column('tipo', sa.Enum('TEXTO', 'AUDIO', 'IMAGEM', 'DOCUMENTO', name='tipomensagem'), nullable=False, server_default='TEXTO'),
        sa.Column('conteudo', sa.Text(), nullable=False),
        sa.Column('midia_url', sa.String(length=500), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('lida', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('criado_em', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('atualizado_em', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['conversa_id'], ['conversas.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Índices para mensagens
    op.create_index(op.f('ix_mensagens_conversa_id'), 'mensagens', ['conversa_id'], unique=False)
    op.create_index(op.f('ix_mensagens_timestamp'), 'mensagens', ['timestamp'], unique=False)


def downgrade() -> None:
    """Remover tabelas de conversas e mensagens."""

    # Remover índices e tabela de mensagens
    op.drop_index(op.f('ix_mensagens_timestamp'), table_name='mensagens')
    op.drop_index(op.f('ix_mensagens_conversa_id'), table_name='mensagens')
    op.drop_table('mensagens')

    # Remover índices e tabela de conversas
    op.drop_index(op.f('ix_conversas_paciente_telefone'), table_name='conversas')
    op.drop_index('ix_conversa_cliente_telefone', table_name='conversas')
    op.drop_table('conversas')

    # Remover enums
    op.execute("DROP TYPE IF EXISTS tipomensagem")
    op.execute("DROP TYPE IF EXISTS remetentemensagem")
    op.execute("DROP TYPE IF EXISTS direcaomensagem")
    op.execute("DROP TYPE IF EXISTS statusconversa")
