"""add onboarding fields to clientes

Revision ID: j01_onboarding_fields
Revises: i02_add_medico_vinculado
Create Date: 2026-01-28

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'j01_onboarding_fields'
down_revision: Union[str, None] = 'i02_add_medico_vinculado'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Status do cliente no fluxo de onboarding
    op.add_column('clientes',
        sa.Column('status', sa.String(30), server_default='ativo', nullable=False)
    )

    # Token de ativação
    op.add_column('clientes',
        sa.Column('token_ativacao', sa.String(100), nullable=True)
    )
    op.create_index('ix_clientes_token_ativacao', 'clientes', ['token_ativacao'], unique=True)

    op.add_column('clientes',
        sa.Column('token_expira_em', sa.DateTime(timezone=True), nullable=True)
    )

    # Quem cadastrou
    op.add_column('clientes',
        sa.Column('cadastrado_por_id', sa.Integer(), nullable=True)
    )
    op.add_column('clientes',
        sa.Column('cadastrado_por_tipo', sa.String(20), nullable=True)
    )

    # Aceite de termos
    op.add_column('clientes',
        sa.Column('aceite_termos_em', sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column('clientes',
        sa.Column('aceite_ip', sa.String(45), nullable=True)
    )
    op.add_column('clientes',
        sa.Column('aceite_user_agent', sa.Text(), nullable=True)
    )
    op.add_column('clientes',
        sa.Column('aceite_versao_termos', sa.String(10), nullable=True)
    )
    op.add_column('clientes',
        sa.Column('aceite_versao_privacidade', sa.String(10), nullable=True)
    )

    # Retrocompatibilidade: clientes existentes mantêm status correto
    op.execute("UPDATE clientes SET status = 'ativo' WHERE ativo = true")
    op.execute("UPDATE clientes SET status = 'suspenso' WHERE ativo = false")


def downgrade() -> None:
    op.drop_index('ix_clientes_token_ativacao', table_name='clientes')
    op.drop_column('clientes', 'aceite_versao_privacidade')
    op.drop_column('clientes', 'aceite_versao_termos')
    op.drop_column('clientes', 'aceite_user_agent')
    op.drop_column('clientes', 'aceite_ip')
    op.drop_column('clientes', 'aceite_termos_em')
    op.drop_column('clientes', 'cadastrado_por_tipo')
    op.drop_column('clientes', 'cadastrado_por_id')
    op.drop_column('clientes', 'token_expira_em')
    op.drop_column('clientes', 'token_ativacao')
    op.drop_column('clientes', 'status')
