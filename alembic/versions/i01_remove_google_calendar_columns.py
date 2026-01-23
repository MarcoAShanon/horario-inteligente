"""Remove Google Calendar integration columns

Revision ID: i01_rm_gcal
Revises: h03_cli_parceiros
Create Date: 2026-01-23

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'i01_rm_gcal'
down_revision: Union[str, None] = 'h15_asaas_integration'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Remove Google Calendar columns from medicos table
    op.drop_column('medicos', 'calendario_id')
    op.drop_column('medicos', 'google_calendar_token')
    op.drop_column('medicos', 'calendario_ativo')

    # Remove Google Calendar columns from configuracoes table
    op.drop_column('configuracoes', 'google_credentials')
    op.drop_column('configuracoes', 'google_calendar_ativo')


def downgrade() -> None:
    # Restore Google Calendar columns in medicos table
    op.add_column('medicos', sa.Column('calendario_id', sa.String(200), nullable=True))
    op.add_column('medicos', sa.Column('google_calendar_token', sa.Text(), nullable=True))
    op.add_column('medicos', sa.Column('calendario_ativo', sa.Boolean(), server_default='false'))

    # Restore Google Calendar columns in configuracoes table
    op.add_column('configuracoes', sa.Column('google_credentials', sa.JSON(), nullable=True))
    op.add_column('configuracoes', sa.Column('google_calendar_ativo', sa.Boolean(), server_default='false'))
