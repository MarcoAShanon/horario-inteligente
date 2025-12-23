"""Create log_auditoria table

Revision ID: h05_auditoria
Revises: h04_custos
Create Date: 2025-12-21

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = 'h05_auditoria'
down_revision: Union[str, None] = 'h04_custos'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'log_auditoria',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),

        # Quem realizou a ação
        sa.Column('usuario_id', sa.Integer(), nullable=True),
        sa.Column('usuario_tipo', sa.String(50), nullable=False),
        # 'admin', 'financeiro', 'suporte', 'medico', 'secretaria', 'sistema'
        sa.Column('usuario_nome', sa.String(255), nullable=True),
        sa.Column('usuario_email', sa.String(255), nullable=True),

        # Cliente afetado (para ações em dados de clientes)
        sa.Column('cliente_id', sa.Integer(), nullable=True),

        # Ação realizada
        sa.Column('acao', sa.String(100), nullable=False),
        # Exemplos: 'login', 'logout', 'criar', 'atualizar', 'deletar', 'visualizar',
        # 'exportar', 'importar', 'aprovar', 'rejeitar', 'enviar_email', etc.

        # Recurso afetado
        sa.Column('recurso', sa.String(100), nullable=True),
        # Exemplos: 'cliente', 'agendamento', 'paciente', 'usuario', 'fatura', etc.
        sa.Column('recurso_id', sa.Integer(), nullable=True),

        # Detalhes da mudança
        sa.Column('dados_anteriores', JSONB, nullable=True),
        sa.Column('dados_novos', JSONB, nullable=True),
        sa.Column('descricao', sa.Text(), nullable=True),

        # Contexto da requisição
        sa.Column('ip_address', sa.String(45), nullable=True),  # Suporta IPv6
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('endpoint', sa.String(255), nullable=True),
        sa.Column('metodo_http', sa.String(10), nullable=True),

        # Resultado da ação
        sa.Column('sucesso', sa.Boolean(), server_default='true'),
        sa.Column('erro_mensagem', sa.Text(), nullable=True),

        # Timestamp
        sa.Column('criado_em', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Índices para buscas e relatórios
    op.create_index('ix_log_auditoria_usuario', 'log_auditoria', ['usuario_id', 'usuario_tipo'])
    op.create_index('ix_log_auditoria_cliente', 'log_auditoria', ['cliente_id'])
    op.create_index('ix_log_auditoria_acao', 'log_auditoria', ['acao'])
    op.create_index('ix_log_auditoria_recurso', 'log_auditoria', ['recurso', 'recurso_id'])
    op.create_index('ix_log_auditoria_criado_em', 'log_auditoria', ['criado_em'])

    # Índice composto para consultas por período e usuário
    op.create_index('ix_log_auditoria_periodo_usuario', 'log_auditoria', ['criado_em', 'usuario_id'])

    # Índice para busca por IP (segurança)
    op.create_index('ix_log_auditoria_ip', 'log_auditoria', ['ip_address'])


def downgrade() -> None:
    op.drop_index('ix_log_auditoria_ip', table_name='log_auditoria')
    op.drop_index('ix_log_auditoria_periodo_usuario', table_name='log_auditoria')
    op.drop_index('ix_log_auditoria_criado_em', table_name='log_auditoria')
    op.drop_index('ix_log_auditoria_recurso', table_name='log_auditoria')
    op.drop_index('ix_log_auditoria_acao', table_name='log_auditoria')
    op.drop_index('ix_log_auditoria_cliente', table_name='log_auditoria')
    op.drop_index('ix_log_auditoria_usuario', table_name='log_auditoria')
    op.drop_table('log_auditoria')
