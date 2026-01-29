"""create historico_inadimplencia table

Revision ID: j04_historico_inadimplencia
Revises: j03_parceiro_auth
Create Date: 2026-01-28

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'j04_historico_inadimplencia'
down_revision: Union[str, None] = 'j03_parceiro_auth'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Criar tabela apenas se não existir (pode ter sido criada manualmente)
    conn = op.get_bind()
    result = conn.execute(sa.text(
        "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'historico_inadimplencia')"
    ))
    table_exists = result.scalar()

    if not table_exists:
        op.create_table(
            'historico_inadimplencia',
            sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
            sa.Column('cliente_id', sa.Integer, sa.ForeignKey('clientes.id'), nullable=False),
            sa.Column('asaas_payment_id', sa.String(50), nullable=True),
            sa.Column('evento', sa.String(30), nullable=False),  # SUSPENSAO, REATIVACAO
            sa.Column('data_evento', sa.DateTime, server_default=sa.func.now(), nullable=False),
            sa.Column('observacoes', sa.Text, nullable=True),
        )

    # Criar índices se não existirem
    conn.execute(sa.text(
        "CREATE INDEX IF NOT EXISTS ix_historico_inadimplencia_cliente_id ON historico_inadimplencia (cliente_id)"
    ))
    conn.execute(sa.text(
        "CREATE INDEX IF NOT EXISTS ix_historico_inadimplencia_evento ON historico_inadimplencia (evento)"
    ))

    # Garantir que a coluna observacoes existe (pode faltar se tabela foi criada parcialmente)
    result = conn.execute(sa.text(
        "SELECT EXISTS (SELECT FROM information_schema.columns "
        "WHERE table_name = 'historico_inadimplencia' AND column_name = 'observacoes')"
    ))
    if not result.scalar():
        op.add_column('historico_inadimplencia', sa.Column('observacoes', sa.Text, nullable=True))


def downgrade() -> None:
    op.drop_index('ix_historico_inadimplencia_evento')
    op.drop_index('ix_historico_inadimplencia_cliente_id')
    op.drop_table('historico_inadimplencia')
