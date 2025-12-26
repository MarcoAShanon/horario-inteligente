"""add horarios_por_dia column

Revision ID: h12_horarios_por_dia
Revises: h11_preferencia_audio
Create Date: 2025-12-24

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'h12_horarios_por_dia'
down_revision = 'h11_preferencia_audio'
branch_labels = None
depends_on = None


def upgrade():
    # Adicionar coluna horarios_por_dia para configuração de horários individuais por dia
    op.add_column('configuracoes_medico',
        sa.Column('horarios_por_dia', sa.Text(), nullable=True,
                  comment='JSON com horários específicos por dia da semana')
    )


def downgrade():
    op.drop_column('configuracoes_medico', 'horarios_por_dia')
