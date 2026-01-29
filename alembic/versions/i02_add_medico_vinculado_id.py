"""add medico_vinculado_id to medicos

Revision ID: i02_add_medico_vinculado_id
Revises: i01_remove_google_calendar_columns
Create Date: 2025-01-27

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'i02_add_medico_vinculado'
down_revision: Union[str, None] = 'i01_rm_gcal'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Adicionar coluna medico_vinculado_id para vincular secretária a um médico
    op.add_column('medicos',
        sa.Column('medico_vinculado_id', sa.Integer(), nullable=True)
    )

    # Adicionar foreign key
    op.create_foreign_key(
        'fk_medicos_medico_vinculado',
        'medicos', 'medicos',
        ['medico_vinculado_id'], ['id']
    )


def downgrade() -> None:
    # Remover foreign key
    op.drop_constraint('fk_medicos_medico_vinculado', 'medicos', type_='foreignkey')

    # Remover coluna
    op.drop_column('medicos', 'medico_vinculado_id')
