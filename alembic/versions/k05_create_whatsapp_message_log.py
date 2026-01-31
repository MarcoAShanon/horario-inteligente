"""create whatsapp_message_log table

Revision ID: k05_whatsapp_msg_log
Revises: k04_add_is_demo_clientes
Create Date: 2026-01-29

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'k05_whatsapp_msg_log'
down_revision: Union[str, None] = 'k04_add_is_demo_clientes'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    # Criar tabela se nao existir
    result = conn.execute(sa.text(
        "SELECT EXISTS (SELECT FROM information_schema.tables "
        "WHERE table_name = 'whatsapp_message_log')"
    ))
    if not result.scalar():
        op.create_table(
            'whatsapp_message_log',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('cliente_id', sa.Integer(), sa.ForeignKey('clientes.id'), nullable=True),
            sa.Column('template_name', sa.String(100), nullable=True),
            sa.Column('message_type', sa.String(30), nullable=False),
            sa.Column('category', sa.String(20), nullable=False),
            sa.Column('phone_to', sa.String(20), nullable=True),
            sa.Column('success', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('message_id', sa.String(200), nullable=True),
            sa.Column('cost_usd', sa.Numeric(10, 6), nullable=False, server_default='0'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        )

        op.create_index('idx_wml_cliente_id', 'whatsapp_message_log', ['cliente_id'])
        op.create_index('idx_wml_created_at', 'whatsapp_message_log', ['created_at'])
        op.create_index('idx_wml_cliente_created', 'whatsapp_message_log', ['cliente_id', 'created_at'])


def downgrade() -> None:
    op.drop_index('idx_wml_cliente_created', table_name='whatsapp_message_log')
    op.drop_index('idx_wml_created_at', table_name='whatsapp_message_log')
    op.drop_index('idx_wml_cliente_id', table_name='whatsapp_message_log')
    op.drop_table('whatsapp_message_log')
