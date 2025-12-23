"""Add preferencia_audio to pacientes

Revision ID: h11_preferencia_audio
Revises: h10_parceria_estrategica
Create Date: 2025-12-23

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'h11_preferencia_audio'
down_revision = 'h10_parceria_estrategica'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Adicionar campo preferencia_audio na tabela pacientes
    # Valores: 'auto' (espelho), 'sempre' (híbrido), 'nunca' (só texto)
    op.add_column(
        'pacientes',
        sa.Column(
            'preferencia_audio',
            sa.String(20),
            nullable=False,
            server_default='auto',
            comment='auto=espelho, sempre=híbrido, nunca=só texto'
        )
    )


def downgrade() -> None:
    op.drop_column('pacientes', 'preferencia_audio')
