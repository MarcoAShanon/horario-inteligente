"""create_notificacoes_medico_table

Revision ID: 6bb8e2ca6b09
Revises: 91f954408749
Create Date: 2025-12-01 23:05:33.089813

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6bb8e2ca6b09'
down_revision: Union[str, Sequence[str], None] = '91f954408749'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'notificacoes_medico',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('medico_id', sa.Integer(), nullable=False),
        sa.Column('cliente_id', sa.Integer(), nullable=False),

        # Configurações de eventos
        sa.Column('notificar_novos', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('notificar_reagendamentos', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('notificar_cancelamentos', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('notificar_confirmacoes', sa.Boolean(), server_default='false', nullable=False),

        # Configurações de canais
        sa.Column('canal_whatsapp', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('canal_email', sa.Boolean(), server_default='false', nullable=False),

        # Dados de contato
        sa.Column('whatsapp_numero', sa.String(length=20), nullable=True),
        sa.Column('email', sa.String(length=255), nullable=True),

        # Timestamps
        sa.Column('criado_em', sa.DateTime(), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('atualizado_em', sa.DateTime(), server_default=sa.text('NOW()'), nullable=False),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['medico_id'], ['medicos.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['cliente_id'], ['clientes.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('medico_id', 'cliente_id', name='unique_medico_cliente_notificacoes')
    )

    # Criar índices
    op.create_index('idx_notificacoes_medico_medico', 'notificacoes_medico', ['medico_id'])
    op.create_index('idx_notificacoes_medico_cliente', 'notificacoes_medico', ['cliente_id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('idx_notificacoes_medico_cliente', table_name='notificacoes_medico')
    op.drop_index('idx_notificacoes_medico_medico', table_name='notificacoes_medico')
    op.drop_table('notificacoes_medico')
